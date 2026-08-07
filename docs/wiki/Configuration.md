# Configuration

[← Back to Home](Home.md)

## `backend/.env`

Copy `backend/templates/.env-template` to `backend/.env` (gitignored) and
fill it in. This is loaded by `backend/config.py` via `python-dotenv`.

| Variable | Meaning |
|---|---|
| `DB_HOST` | MariaDB hostname. `mariadb` when running via compose (resolves inside the Podman/Docker network); `localhost` if connecting from the host. |
| `DB_PORT` | MariaDB port. `3306` in-container; `5001` from the host (the published port in `docker-compose.yml`). |
| `DB_USER` / `DB_PASSWORD` / `DB_NAME` | Must match the `MARIADB_*` values in `docker-compose.yml`'s `mariadb` service (defaults: `ootp` / `supersecretpw` / `ootp`). |
| `GAME_PATH` | Path to your OOTP save's directory (used for reference/tooling around the save itself, not the dump ingestion path). |
| `DUMP_PATH` | Where the backend looks for dump heap folders (`dump_YYYY_MM`, `dump_YYYY_yearly`). Inside the container this is `/data/dumps` — see the bind mount below. |
| `ADMIN_API_TOKEN` | Shared-secret token required to call the `/api/admin/*` routes (the `X-Admin-Token` header). Generate one with `python -c "import secrets; print(secrets.token_hex(32))"`. See [Admin API](Admin-API.md). |

## Pointing the app at your OOTP save

`DUMP_PATH=/data/dumps` in `.env` is the path *inside the backend
container* — it doesn't point anywhere on your host by itself. The actual
host folder is wired up via a bind mount in `docker-compose.yml`:

```yaml
services:
  backend:
    volumes:
      - ./backend:/app:Z
      - "/path/to/your/saved_games/<save_name>/dump:/data/dumps:Z"
```

Edit that second line to point at your own OOTP `saved_games/<save>/dump`
folder before bringing the stack up. The `:Z` suffix is required for
rootless Podman on SELinux-enforcing hosts (e.g. Fedora) — without it,
containers fail at startup with permission-denied errors reading their own
mounted source/`.env`.

## Running backend commands from the host instead of a container

`backend/.env` is tuned for in-container execution. Running `flask` commands
from the host `.venv` needs the DB/dump values overridden on the command
line, since `DB_HOST=mariadb` and `DUMP_PATH=/data/dumps` don't resolve
outside the container network:

```bash
cd backend
DB_HOST=localhost DB_PORT=5001 DB_USER=ootp DB_PASSWORD=supersecretpw DB_NAME=ootp \
DUMP_PATH="/absolute/host/path/to/saved_games/<save>/dump" \
.venv/bin/flask --app app update-db
```

This friction is exactly what the [Admin API](Admin-API.md) exists to avoid
— it runs the same operations inside the container, where the plain `.env`
values already resolve correctly.
