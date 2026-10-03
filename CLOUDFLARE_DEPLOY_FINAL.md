# FloodAlert — Cloudflare Workers Build (Final v2)

## Workers Builds settings

Build command:

    pipx install uv --force

Deploy command:

    uvx --from workers-py pywrangler deploy

Preview command:

    uvx --from workers-py pywrangler dev

IMPORTANT: do not keep a requirements.txt in the repository. Pywrangler vendors Python packages from pyproject.toml. Cloudflare currently documents pyproject.toml + pywrangler as the Python Workers package/deploy path.

## Runtime

- Worker name: floodalert
- Main: src/worker.py
- compatibility flag: python_workers
- Hyperdrive binding: HYPERDRIVE
- Hyperdrive ID: 281ea631f8b34ec9852e9f7669c7f4f4

## Required secrets

Set in Worker Variables/Secrets:
- SECRET_KEY
- TMD_ACCESS_TOKEN

Do not put passwords/tokens in GitHub. Supabase PostgreSQL credentials are stored in Hyperdrive.
