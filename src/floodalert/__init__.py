import os
from urllib.parse import quote

from dotenv import load_dotenv
from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from sqlalchemy.pool import NullPool

try:
    import bcrypt as _bcrypt
except ImportError:  # pragma: no cover - normal local install includes bcrypt
    _bcrypt = None


load_dotenv()


db = SQLAlchemy()
login_manager = LoginManager()


class _PasswordHasher:
    """Small Flask-Bcrypt-compatible adapter backed by bcrypt.

    Cloudflare Python Workers already ships a Pyodide-compatible bcrypt build,
    so this avoids pulling in Flask-Bcrypt as an extra extension while keeping
    the same bcrypt password hash format used by the existing app.
    """

    def generate_password_hash(self, password):
        if _bcrypt is None:
            raise RuntimeError("bcrypt is not installed")
        value = password.encode("utf-8") if isinstance(password, str) else password
        return _bcrypt.hashpw(value, _bcrypt.gensalt())

    def check_password_hash(self, password_hash, password):
        if _bcrypt is None:
            raise RuntimeError("bcrypt is not installed")
        stored = password_hash.encode("utf-8") if isinstance(password_hash, str) else password_hash
        value = password.encode("utf-8") if isinstance(password, str) else password
        try:
            return _bcrypt.checkpw(value, stored)
        except (ValueError, TypeError):
            return False


bcrypt = _PasswordHasher()


def _normalize_database_url(database_url):
    value = (database_url or "").strip()
    if value.startswith("postgres://"):
        return "postgresql+pg8000://" + value[len("postgres://"):]
    if value.startswith("postgresql://"):
        return "postgresql+pg8000://" + value[len("postgresql://"):]
    return value


def create_app(
    database_url=None,
    secret_key=None,
    start_background_scheduler=True,
    engine_options=None,
):
    base_dir = os.path.dirname(os.path.abspath(__file__))

    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, "templates"),
        static_folder=os.path.join(base_dir, "static"),
    )

    app.config["SECRET_KEY"] = secret_key or os.getenv(
        "SECRET_KEY",
        "flood-alert-secret-key",
    )

    normalized_db_url = _normalize_database_url(
        database_url or os.getenv("DATABASE_URL", "sqlite:///flood_alert.db")
    )
    app.config["SQLALCHEMY_DATABASE_URI"] = normalized_db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    default_engine_options = {
        "pool_pre_ping": True,
        "pool_recycle": 1800,
    }
    if engine_options:
        default_engine_options.update(engine_options)
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = default_engine_options

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "กรุณาเข้าสู่ระบบเพื่อเปิดพื้นที่ของฉัน"
    login_manager.login_message_category = "info"

    from .auth import auth
    from .main import main

    app.register_blueprint(auth)
    app.register_blueprint(main)

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    with app.app_context():
        db.create_all()
        _migrate_tracked_area(app)

    if start_background_scheduler and (
        not os.environ.get("CLOUDFLARE_WORKERS")
        and not os.environ.get("VERCEL")
        and (
            not app.debug
            or os.environ.get("WERKZEUG_RUN_MAIN") == "true"
        )
    ):
        from .scheduler import start_scheduler
        start_scheduler(app)

    return app


def build_hyperdrive_database_url(hyperdrive):
    """Build an SQLAlchemy pg8000 URL from a Cloudflare Hyperdrive binding."""
    user = quote(str(hyperdrive.user), safe="")
    password = quote(str(hyperdrive.password), safe="")
    host = str(hyperdrive.host)
    port = int(hyperdrive.port)
    database = quote(str(hyperdrive.database), safe="")
    return f"postgresql+pg8000://{user}:{password}@{host}:{port}/{database}"


def hyperdrive_engine_options():
    """Engine options suitable for Cloudflare Hyperdrive + synchronous SQLAlchemy."""
    return {
        "poolclass": NullPool,
        "pool_pre_ping": False,
        "connect_args": {
            # Hyperdrive terminates TLS before forwarding to the Worker socket.
            "ssl_context": False,
        },
    }


def _migrate_tracked_area(app):
    """Add the optional subdistrict column to an existing schema."""
    inspector = inspect(db.engine)

    if not inspector.has_table("tracked_area"):
        return

    columns = {
        column["name"]
        for column in inspector.get_columns("tracked_area")
    }

    if "subdistrict" in columns:
        return

    db.session.execute(
        text(
            "ALTER TABLE tracked_area "
            "ADD COLUMN subdistrict VARCHAR(100)"
        )
    )
    db.session.commit()
