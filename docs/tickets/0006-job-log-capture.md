# 0006 — Capture per-line logs for update-db jobs

- **Tag:** feat
- **Status:** Open
- **Depends on:** [0004](0004-async-update-db-job.md), [0005](0005-frontend-admin-trigger.md)
- **Blocks:** —

## 1. Problem

While scoping [0005](0005-frontend-admin-trigger.md) (the frontend admin
trigger), a live log tail for in-flight `update-db` jobs was the preferred
progress UI — but the job record added in
[0004](0004-async-update-db-job.md) (`app/db/jobs.py`) only stores
`status`/`result`/`error`. The actual progress narrative
(`check_new_heaps` results, per-heap "Migrating..." lines, projection counts)
only goes to `current_app.logger` inside `app/db/update.py` /
`app/db/service.py::update_database()`, which isn't captured anywhere a
client can read it. 0005 shipped with a simple status indicator instead
(poll `GET /api/admin/jobs/{id}`, show pending/running/succeeded/failed) —
this ticket is the deferred follow-up to add the log tail on top of that.

## 2. Design choices

- **Capture mechanism.** Options considered:
  - (a) Attach a per-job `logging.Handler` that appends formatted records
    into the job's registry entry, installed on the relevant loggers
    (`api/db/update`, `api/db/service`, or the root logger) for the
    duration of the job.
  - (b) Thread an explicit `log(line)` callback through
    `update_database()` → `process_single_heap()` → the migration/projection
    helpers, replacing/augmenting the existing `logger.info(...)` calls.
  - **Recommendation (not yet decided):** (a) is less invasive — no changes
    to `update.py`'s internals or function signatures (keeping with 0001's
    "don't touch ingestion internals" precedent) — and thread-scoping the
    handler (filter on thread id) is simple since 0004 already guarantees
    only one job runs at a time. (b) is more explicit/testable but touches
    more files.
- **Storage shape.** Append lines to a `logs: list[str]` (or
  `list[{"ts": ..., "message": ...}]`) field on the job record. Unbounded for
  now — a full year of dumps produces a bounded, known number of log lines,
  not an issue at current scale.
- **Delivery to the frontend.** Options considered:
  - (a) `GET /api/admin/jobs/{id}` returns the full `logs` list each poll (05's
    polling interval, e.g. every 1-2s) — simplest, reuses the existing route.
  - (b) A `since` cursor/offset param so the client only fetches new lines.
  - (c) Server-Sent Events / WebSocket push.
  - **Leaning towards (a)** first — full-list polling — since job logs are
    small and finite; upgrade to (b)/(c) only if that proves too chatty.
- **Outstanding:** none of the above is finalized — this ticket needs its own
  design pass before implementation, this is a placeholder scoped from 0005's
  design discussion, not a ready-to-build plan.

## 3. Approach

Not yet planned in detail. Expected shape once scoped:

- Extend the job record in `backend/app/db/jobs.py` with a `logs` field.
- Wire up log capture per the chosen mechanism above.
- Extend `GET /api/admin/jobs/{job_id}` (`backend/app/api/admin.py`) to
  include `logs` in the response; update `backend/docs/openai.yaml`.
- Update the frontend admin page (added in
  [0005](0005-frontend-admin-trigger.md)) to render the log lines instead of
  just the status indicator.

**Files involved:** TBD — revisit before implementation.
