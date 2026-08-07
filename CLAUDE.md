# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

OOTP25-Toolbox parses OOTP Baseball 25 MySQL dump exports and turns them into
analytics/projections (player search, batter projections, run-value estimates,
percentile profiles) via a Flask API + Vue 3 frontend, backed by MariaDB.

## Commands

### Run the full stack

```bash
podman compose up -d      # or: docker-compose up --build
```

- Backend: `localhost:5000`
- Frontend: `localhost:5173`
- MariaDB: published on host port `5001` (container port `3306`)

Bind mounts in `docker-compose.yml` use the `:Z` SELinux relabel flag (required
for rootless Podman on SELinux-enforcing hosts, e.g. Fedora). Without it,
containers fail at startup with permission-denied errors reading their own
mounted source/`.env`.

### Backend — dependencies & tests

Backend uses `uv` (`backend/pyproject.toml`, `backend/uv.lock`, Python 3.13).

```bash
cd backend
uv venv                        # first-time setup
uv pip install --system .      # or `uv sync`
.venv/bin/pytest                        # all tests (pytest.ini sets pythonpath = .)
.venv/bin/pytest tests/db/test_update.py           # single file
.venv/bin/pytest tests/db/test_update.py::test_foo -v   # single test
```

### Frontend

```bash
cd frontend
npm run dev       # vite dev server, host 0.0.0.0:5173
npm run build      # vue-tsc -b && vite build (type-checks first)
npm run preview
```

### Database init/update CLI

```bash
cd backend
flask --app app init-db     # (re)creates schema from app/db/sql_scripts/schema.sql
flask --app app update-db   # ingests new dump heaps, migrates, projects players
```

**Running these from the host `.venv` (as opposed to inside the backend
container) requires overriding env vars**, because `backend/.env` is tuned for
in-container execution:

```bash
DB_HOST=localhost DB_PORT=5001 DB_USER=ootp DB_PASSWORD=supersecretpw DB_NAME=ootp \
DUMP_PATH="/absolute/host/path/to/saved_games/<save>/dump" \
.venv/bin/flask --app app update-db
```

`DB_HOST=mariadb` only resolves inside the Podman/Docker network, and
`DUMP_PATH=/data/dumps` is the *container's* bind-mount target, not a host
path — `init-db` needs the DB overrides, `update-db` needs both.

## Architecture

### Data pipeline (the core mechanic of this app)

OOTP exports per-table `.mysql.sql` dump files into
`saved_games/<save>/dump/dump_YYYY_MM/mysql/` (monthly = "short" heap) and
`dump_YYYY_yearly/mysql/` (yearly = "long" heap). `flask update-db` drives:

1. **`app/db/staging.py`** (`check_new_heaps`, `load_sql_dumps_into_staging`) —
   scans `DUMP_PATH` for heap directories, loads only the tables in
   `DUMP_INCLUSION_LIST` (players, players_batting/fielding/pitching,
   players_career_batting_stats, teams) into a separate **`staging`** MariaDB
   database (raw, unmodified OOTP schema — see `mariadb/init-staging.sql`).
2. **`app/db/update.py`** (`process_single_heap`) — runs a SQL migration script
   from staging into the main **`ootp`** database:
   - **Long/yearly heaps** (`migration_long.sql`) seed the base `players` and
     `teams` tables and update player ages.
   - **Short/monthly heaps** (`migration_short.sql`) only *add* a dated rating
     snapshot per player (`players_rating` + `players_batting`/`fielding`/
     `basepath` etc.), via `INSERT IGNORE ... FOREIGN KEY (player_id)
     REFERENCES players(player_id)`.
   - **Important:** a short heap run against an empty `players` table silently
     inserts nothing everywhere (FK-guarded `INSERT IGNORE` no-ops). At least
     one yearly dump must be present and processed before monthly dumps are
     useful — this matches the README's instruction to always keep a yearly
     dump in the folder.
3. For short heaps, `app/db/projection.py` + `app/player_projection/batter.py`
   (`BatterProjection`) compute expected stats/WAR from the new ratings and
   insert into the `*_expected` and `players_run_value` tables.

Heap dates are threaded through migration SQL via `{{HEAP_DATE}}` templating
(`app/db/migration.py::inject_heap_date`), not query parameters.

### Backend structure

- **`app/__init__.py`** — `create_app()` factory: loads `config.DevConfig` /
  `ProdConfig`, calls `db.init_app(app)`, registers API blueprints.
- **`app/db/__init__.py`** — registers the `init-db`/`update-db` Flask CLI
  commands (`app/db/cli.py`) and the per-request DB teardown.
- **`app/db/connection.py`** — `get_db()`/`close_db()`: one `pymysql` connection
  per request via Flask's `g`, `DictCursor` results. Every route pattern is
  `get_db()` → work in a `try` → `close_db()` in `finally`.
- **`app/api/*.py`** — one blueprint per resource (`players`, `ratings`,
  `projections`), each with its own `url_prefix`. Simple queries are inlined;
  non-trivial ones are loaded from `.sql` files under
  `app/db/sql_scripts/api/` via `current_app.open_resource(...)`.
- **`backend/docs/openai.yaml`** — OpenAPI spec documenting the API routes;
  keep in sync when adding/changing endpoints.
- Config (`backend/config.py`) loads `backend/.env` via `python-dotenv`
  (`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DUMP_PATH`,
  `GAME_PATH`). `.env` is gitignored; copy from `backend/templates/.env-template`.

### Frontend structure

Vue 3 + TypeScript + Vite + Tailwind v4 + Pinia + vue-router.
`vite.config.ts` proxies `/api` to `http://backend:5000` (only resolves inside
the Podman/Docker network — running `vite` standalone on the host needs the
proxy target adjusted or the backend reached directly).

### Ticket tracking

Planned/in-progress work is tracked as tickets in `docs/tickets/`, indexed in
`docs/tickets/index.md`. New tickets should be based on `docs/tickets/TEMPLATE.md`
(problem / design choices / chosen approach / files involved, tagged
`feat|fix|chore|refactor`, status `Open|In-Progress|Closed`) and linked from
the index.
