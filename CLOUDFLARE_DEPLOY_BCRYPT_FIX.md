# FloodAlert Cloudflare bcrypt fix

The previous deployment failed because Cloudflare Pyodide could not resolve `bcrypt==4.3.0`.
The current Pyodide package index provides `bcrypt==5.0.0`, so this build pins `bcrypt==5.0.0`.

Workers Builds:
- Build command: `pipx install uv --force`
- Deploy command: `uvx --from workers-py pywrangler deploy`

Do not add a `requirements.txt`; Python Worker dependencies belong in `pyproject.toml`.
Hyperdrive binding remains the existing `flood-alert-db` configuration.
