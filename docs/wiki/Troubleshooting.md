# Troubleshooting

[← Back to Home](Home.md)

## Containers fail at startup with permission-denied errors

**Cause:** on rootless Podman with SELinux enforcing (e.g. Fedora), bind
mounts need the `:Z` relabel flag. Without it, containers can't read their
own mounted source/`.env`.

**Fix:** confirm every `volumes:` entry in `docker-compose.yml` ends in
`:Z` (already the default in this repo — check if you've added new mounts).

## `update-db` finds heaps but nothing shows up in the app

**Cause:** monthly ("short") heaps only *add* rating snapshots to existing
players via `INSERT IGNORE ... FOREIGN KEY (player_id) REFERENCES
players(player_id)`. If the `players` table is still empty (no yearly heap
has ever been processed), every monthly insert silently no-ops.

**Fix:** make sure at least one yearly dump (`dump_YYYY_yearly`) is present
in your dump folder and gets processed by `update-db` before relying on
monthly data. See [Updating the Database](Updating-the-Database.md).

## `flask --app app update-db` fails to connect / hangs, run from the host

**Cause:** `backend/.env` is tuned for in-container execution —
`DB_HOST=mariadb` only resolves inside the Podman/Docker network, and
`DUMP_PATH=/data/dumps` is the container's bind-mount target, not a host
path.

**Fix:** override the relevant vars on the command line when running from
the host `.venv` (see [Configuration](Configuration.md)), or use the
[Admin API](Admin-API.md) instead, which always runs inside the container.

## `Admin API` routes return `401 {"error": "unauthorized"}`

**Cause:** either the `X-Admin-Token` header is missing/wrong, or
`ADMIN_API_TOKEN` isn't set in `backend/.env` at all — the routes fail
closed (reject everyone) when unconfigured, rather than allowing
unauthenticated access.

**Fix:** set `ADMIN_API_TOKEN` in `backend/.env`, restart the backend
container, and send the same value as the `X-Admin-Token` header.

## Frontend can't reach the backend when run outside Podman/Docker

**Cause:** `vite.config.ts` proxies `/api` to `http://backend:5000`, which
only resolves inside the Podman/Docker network. Running `npm run dev`
standalone on the host can't reach that hostname.

**Fix:** either run the full stack via compose, or point the proxy target
at `http://localhost:5000` (or wherever the backend container's port `5000`
is published) when running the frontend dev server standalone.

## Backend tests fail with DB/connection errors

Most backend tests mock the DB layer and don't need a live database — a
failure connecting to MariaDB usually means a test is missing a `@patch` for
`get_db`/`close_db`, not a real infrastructure problem. Run a single file to
narrow it down:

```bash
cd backend
.venv/bin/pytest tests/db/test_service.py -v
```
