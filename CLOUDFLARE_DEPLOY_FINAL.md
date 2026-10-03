# FloodAlert — Cloudflare Workers Builds (Python + Flask + Hyperdrive)

## Why the previous deployment failed

Workers Builds was running `npx wrangler deploy` after a normal `pip install -r requirements.txt`.
That installed Python packages only in the build environment; it did not vendor them into the Python Worker bundle. The Worker then failed while importing Cloudflare's `workers.wsgi` adapter.

For Python Workers, Cloudflare documents Pywrangler as the package-management/deployment path. Pywrangler reads `pyproject.toml`, vendors the dependencies, and then deploys the Worker.

## Workers Builds settings

Because the Cloudflare build image includes `pipx` but may not have `uv` preinstalled, use:

Build command:

    pipx install uv --force

Deploy command:

    uvx --from workers-py pywrangler deploy

Preview command:

    uvx --from workers-py pywrangler preview

This keeps the Python Worker packaging step inside Pywrangler while still using Workers Builds for CI/CD.

## Wrangler configuration

`wrangler.jsonc` is already configured with:

- Worker name: `floodalert`
- Main: `src/worker.py`
- Compatibility flag: `python_workers`
- Hyperdrive binding: `HYPERDRIVE`
- Hyperdrive configuration ID: `281ea631f8b34ec9852e9f7669c7f4f4`

Do not replace the Hyperdrive ID with the configuration name.

## Runtime variables / secrets

Set these under the Worker runtime Variables & Secrets area, not the Workers Builds-only build variables:

- `SECRET_KEY` — secret
- `TMD_ACCESS_TOKEN` — secret
- `CRON_SECRET` — secret if you use the optional cron authorization flow

`TMD_FORECAST_URL` and `TMD_WARNING_URL` are already configured in `wrangler.jsonc`.

## Database

The application uses Cloudflare Hyperdrive to connect to the existing Supabase PostgreSQL database. The Supabase database password is stored in the Hyperdrive configuration and is not included in the repository.

## Notes

- Cloudflare's current Flask example uses `from workers import wsgi` and `Default = wsgi.entrypoint(app)`.
- Hyperdrive's Python Workers documentation lists `pg8000` as a tested PostgreSQL driver and states that synchronous SQLAlchemy is supported. Sync DB operations should be serialized with a lock; this project already does that in `src/worker.py`.
