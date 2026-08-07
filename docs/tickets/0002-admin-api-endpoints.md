# 0002 — Admin API endpoints for init-db and update-db

- **Tag:** feat
- **Status:** Closed
- **Depends on:** [0001](0001-extract-db-service-layer.md)
- **Blocks:** [0003](0003-admin-api-auth-guard.md), [0004](0004-async-update-db-job.md)

## 1. Problem

`init-db` and `update-db` are currently only reachable via the Flask CLI
(`flask --app app init-db` / `update-db`). Running them from the host requires
manually overriding `DB_HOST`, `DB_PORT`, and `DUMP_PATH` because `.env` is tuned
for in-container execution (`DB_HOST=mariadb`, `DUMP_PATH=/data/dumps`), which
doesn't resolve from the host. This has already caused repeated friction locally.

Exposing the same operations as backend API routes sidesteps that mismatch
entirely — the route runs inside the backend container, where the existing env
config is already correct — and also allows triggering them from a future UI
button or a plain `curl` call instead of a local `.venv`.

## 2. Design choices

- **Blueprint & routing.** New `backend/app/api/admin.py` blueprint, following the
  existing convention in `app/api/players.py` / `ratings.py` / `projections.py`,
  registered with `url_prefix="/api/admin"`:
  - `POST /api/admin/init-db`
  - `POST /api/admin/update-db`
- **Response contract.** `200` with the service function's result dict on success;
  `500` with `{"error": str(e)}` on failure, matching the existing error style used
  in `ratings.py` (`{"error": "..."}`, non-200 status).
- **Scope of `update-db`.** Mirrors current CLI behavior exactly — no request
  parameters, always processes whatever `check_new_heaps()` finds under
  `DUMP_PATH`. Parameterizing which heap(s) to run is out of scope here.
- **Sync vs. async.** This ticket ships both routes as plain synchronous request
  handlers. `update-db` can run for tens of seconds to minutes on a full year of
  dumps, which risks request/gateway timeouts and blocks the worker thread — that
  gap is intentionally deferred to [0004](0004-async-update-db-job.md) so this
  ticket stays small and independently reviewable.
- **No auth in this ticket.** These routes are destructive (`init-db` drops and
  recreates the schema). Access control is handled separately in
  [0003](0003-admin-api-auth-guard.md) so it can be reviewed as its own concern —
  this ticket should not be deployed/merged ahead of 0003 landing.

## 3. Approach

- Add `backend/app/api/admin.py`:
  - `bp = Blueprint("admin", __name__, url_prefix="/api/admin")`
  - `POST ""` → `/init-db`: calls `service.init_database()`, returns JSON.
  - `POST "/update-db"`: calls `service.update_database()`, returns JSON.
- Register the blueprint in `backend/app/__init__.py` alongside the existing
  `players`, `projections`, `ratings` blueprints.
- Document both routes in `backend/docs/openai.yaml` under a new `Admin` tag,
  matching the existing OpenAPI structure used for `Players`/`Ratings`.

**Files involved:**
- `backend/app/api/admin.py` (new)
- `backend/app/__init__.py` (modified — blueprint registration)
- `backend/docs/openai.yaml` (modified — document new routes)
