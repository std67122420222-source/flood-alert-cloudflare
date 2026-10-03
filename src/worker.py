import asyncio
import os

from workers import WorkerEntrypoint, Response, wsgi

from floodalert import (
    build_hyperdrive_database_url,
    create_app,
    hyperdrive_engine_options,
)


_APP = None
_DB_LOCK = asyncio.Lock()


def _set_runtime_environment(env):
    """Expose Worker vars/secrets to the existing Flask modules.

    The current FloodAlert modules intentionally read configuration from
    os.getenv(). We populate those values once per isolate before constructing
    the Flask app.
    """
    keys = (
        "SECRET_KEY",
        "TMD_ACCESS_TOKEN",
        "TMD_FORECAST_URL",
        "TMD_WARNING_URL",
        "TMD_TIMEOUT",
        "TMD_FORECAST_HOURS",
        "TMD_MAX_RETRIES",
        "TMD_RETRY_BASE_SECONDS",
        "TMD_REQUEST_DELAY_SECONDS",
        "TMD_FORECAST_FIELDS",
        "TMD_WARNING_TIMEOUT",
        "TMD_WARNING_CACHE_MINUTES",
        "CRON_SECRET",
    )

    for key in keys:
        value = getattr(env, key, None)
        if value is not None and str(value) != "":
            os.environ[key] = str(value)

    os.environ["CLOUDFLARE_WORKERS"] = "1"


def _get_app(env):
    global _APP

    if _APP is not None:
        return _APP

    _set_runtime_environment(env)

    hyperdrive = getattr(env, "HYPERDRIVE", None)
    if hyperdrive is None:
        raise RuntimeError(
            "HYPERDRIVE binding is missing. Create a Cloudflare Hyperdrive "
            "configuration for the FloodAlert PostgreSQL database and bind it "
            "as HYPERDRIVE in wrangler.jsonc."
        )

    database_url = build_hyperdrive_database_url(hyperdrive)

    _APP = create_app(
        database_url=database_url,
        secret_key=os.getenv("SECRET_KEY", "flood-alert-cloudflare-secret"),
        start_background_scheduler=False,
        engine_options=hyperdrive_engine_options(),
    )
    return _APP


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        """Run the existing Flask app through Cloudflare's WSGI adapter."""
        try:
            app = _get_app(self.env)
        except Exception as exc:
            return Response(
                "FloodAlert configuration error: " + str(exc),
                status=500,
            )

        # Synchronous SQLAlchemy operations should be serialized in Python
        # Workers when using Hyperdrive. This protects concurrent requests from
        # overlapping sync DB/socket operations inside one isolate.
        async with _DB_LOCK:
            return await wsgi.fetch(app, request, self.env)

    async def scheduled(self, controller, env, ctx):
        """Refresh data without a long-lived scheduler thread."""
        try:
            app = _get_app(env)
            with app.app_context():
                cron = str(controller.cron)

                if cron == "*/15 * * * *":
                    from floodalert.weather_service import (
                        collect_forecast_for_tracked_areas,
                    )

                    saved = collect_forecast_for_tracked_areas()
                    print(f"Forecast refresh completed: {saved} records")
                    return

                if cron == "*/10 * * * *":
                    from floodalert.warning_service import sync_weather_warnings

                    saved = sync_weather_warnings()
                    print(f"Warning refresh completed: {saved} records")
                    return

                print(f"No scheduled job for cron: {cron}")
        except Exception as exc:
            print(f"Scheduled refresh failed: {exc}")


__all__ = ["Default"]
