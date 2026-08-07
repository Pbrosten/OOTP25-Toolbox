# 0004 — Run update-db as an async background job with status polling

- **Tag:** feat
- **Status:** Closed
- **Depends on:** [0002](0002-admin-api-endpoints.md), [0003](0003-admin-api-auth-guard.md)
- **Blocks:** [0005](0005-frontend-admin-trigger.md)

## 1. Problem

`update_database()` (via `update_db()` in `app/db/update.py`) loads full dump
files into staging, runs SQL migrations, and projects every player using a
multiprocessing pool — this can take anywhere from seconds to minutes depending
on dump size (a full year of monthly heaps vs. the single-month test dump used
so far). A synchronous `POST /api/admin/update-db` (as shipped in 0002) blocks
the request thread for the entire duration, risking client/gateway timeouts and
giving a future UI button no way to show progress.

## 2. Design choices

- **Job runner.** Options considered:
  - (a) In-process `threading.Thread` + in-memory job-status dict.
  - (b) A real task queue (Celery/RQ + Redis).
  - **Chosen: (a)** for now — no task-queue infra exists in this project, and the
    backend currently runs as a single dev process. **Outstanding:** in-memory
    job state does not work across multiple gunicorn/uwsgi workers or container
    replicas — if this backend ever moves to a multi-worker production
    deployment, this needs to move to (b) or a shared store (DB-backed job table,
    Redis, etc.). Flagged here, not solved.
- **API shape.**
  - `POST /api/admin/update-db` returns `202 Accepted` with `{"job_id": "..."}`
    immediately instead of blocking.
  - New `GET /api/admin/jobs/<job_id>` returns
    `{"status": "pending|running|succeeded|failed", "result": ..., "error": ...}`.
- **Concurrency.** Only one `update-db` job may run at a time. A new request while
  a job is `pending`/`running` is rejected with `409 {"error": "update already in
  progress", "job_id": "..."}` rather than queued — keeps the first implementation
  simple; queuing multiple runs is not a real use case for this tool.
- **`init-db` stays synchronous.** It's fast (schema DDL only) and destructive
  enough that immediate, blocking feedback is preferable to a job you have to
  poll.

## 3. Approach

- Add `backend/app/db/jobs.py`:
  - In-memory registry: `dict[job_id, {"status", "result", "error", "started_at"}]`.
  - `start_update_job() -> job_id`: refuses to start if a job is already
    `pending`/`running`; otherwise generates a `uuid4` job id, launches
    `update_database()` (from 0001) on a `threading.Thread`, updates the registry
    on completion/exception, returns the id.
  - `get_job(job_id) -> dict | None`.
- Modify `backend/app/api/admin.py`:
  - `POST /update-db` now calls `jobs.start_update_job()` and returns `202` (or
    `409` if already running), instead of calling `service.update_database()`
    directly.
  - Add `GET /jobs/<job_id>` returning the job's current status.
  - Both remain behind `@require_admin_token` from [0003](0003-admin-api-auth-guard.md).
- Update `backend/docs/openai.yaml` to reflect the new `202`/`409` responses and
  the `GET /api/admin/jobs/{job_id}` route.

**Files involved:**
- `backend/app/db/jobs.py` (new)
- `backend/app/api/admin.py` (modified)
- `backend/docs/openai.yaml` (modified)
