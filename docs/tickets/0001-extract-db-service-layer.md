# 0001 — Extract DB init/update logic into a reusable service layer

- **Tag:** refactor
- **Status:** Closed
- **Depends on:** —
- **Blocks:** [0002](0002-admin-api-endpoints.md)

## 1. Problem

The logic for initializing the schema and running the dump-ingestion/migration flow
currently lives directly inside the Click command callbacks in
`backend/app/db/cli.py` (`init_db_command`, `update_db_command`). It's coupled to
Click's invocation model and to `click.echo` for reporting results.

We want to trigger the same operations from an HTTP API (see 0002) as well as the
CLI. Click command callbacks can't be called cleanly from a Flask view, so the
underlying logic needs to be extracted into plain, importable functions first.

## 2. Design choices

- **Where does the logic live?** New module `backend/app/db/service.py` containing
  `init_database()` and `update_database()` as plain functions with no Click
  dependency. `cli.py` becomes a thin wrapper: parse nothing, call the service
  function, `click.echo` the result.
- **Return shape.** Service functions return a structured `dict` (e.g.
  `{"status": "ok", "heaps_processed": n, "players": n, "projections": n}`)
  instead of only logging, so an HTTP caller (0002) has something to serialize to
  JSON. Errors are raised as exceptions (existing behavior) rather than swallowed,
  so the caller decides how to translate them (CLI: traceback; API: 500 JSON body).
- **Outstanding:** whether these functions should accept optional progress-report
  callbacks (relevant once 0004 adds background-job status polling) is deferred to
  0004 — not decided here to avoid speculative API surface.

## 3. Approach

- Add `backend/app/db/service.py`:
  - `init_database() -> dict` — the current body of `init_db_command` minus the
    `click.echo` call (schema load + execute, returns a summary dict).
  - `update_database() -> dict` — wraps the existing `update_db()` function in
    `backend/app/db/cli.py`, returning a summary dict instead of relying purely on
    logger output.
- Update `backend/app/db/cli.py`:
  - `init_db_command` and `update_db_command` call the new service functions and
    `click.echo` a short summary of the returned dict. No behavior change for
    existing CLI usage.
- No changes to `backend/app/db/connection.py`, `staging.py`, `update.py`,
  `migration.py`, or `projection.py` — this ticket only moves/wraps the entry
  points, it doesn't touch the ingestion internals.

**Files involved:**
- `backend/app/db/service.py` (new)
- `backend/app/db/cli.py` (modified)
