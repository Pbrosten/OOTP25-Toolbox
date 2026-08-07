# 0010 — Guard the CLI update-db path with the same in-flight-job lock as the API

- **Tag:** fix
- **Status:** Open
- **Depends on:** —
- **Blocks:** —

## 1. Problem

[0004](0004-async-update-db-job.md) added a single-in-flight-job guard
(`backend/app/db/jobs.py`'s `_lock`/`_jobs`), but only the
`POST /api/admin/update-db` route goes through it
(`backend/app/db/cli.py::update_db_command` calls
`service.update_database()` directly, bypassing `jobs.py` entirely).

Two concurrent runs — two CLI invocations, or one CLI run overlapping one
API-triggered job — will both load into the same `staging` schema
concurrently and each spin up their own `Pool(cpu_count())`, doubling CPU
contention and risking cross-run staging data contamination (this risk is
independent of whether [0013](0013-reenable-staging-reset.md)'s reset is
re-enabled — the reset clears staging *before* a run starts, it doesn't
protect two runs interleaving *during* execution).

Low likelihood in a single-operator local tool, but the failure mode
(corrupted staging data feeding both runs' migrations) is silent and hard
to diagnose after the fact.

## 2. Design choices

- **Where the lock lives.** Options considered: (a) keep locking only in
  `jobs.py` and also make the CLI command go through `jobs.py` instead of
  calling `service.update_database()` directly; (b) move the lock into
  `service.update_database()` itself, so both the CLI and the job runner
  inherit protection by construction. **Chosen: (b)** — protection should be
  guaranteed regardless of entry point rather than living only in the
  job-runner layer, since a third future entry point (e.g. a scheduled task)
  would otherwise need to remember to route through `jobs.py` too.
- **CLI behavior on lock conflict.** The CLI command should fail fast with a
  clear message (not silently queue or block) if a job is already running —
  matches the existing API behavior (`409` with an error message).

## 3. Approach

- Move the `threading.Lock`-based "already running" check out of
  `jobs.py::start_update_job()` and into `service.update_database()`, so it
  applies no matter who calls it.
- `jobs.py::start_update_job()` becomes a thin wrapper: call
  `service.update_database()` on a background thread, letting the shared
  lock raise if one's already in flight.
- `cli.py::update_db_command` catches the "already running" exception and
  prints a clear CLI error instead of letting a raw exception surface.

**Files involved:**
- `backend/app/db/service.py` (modified — lock lives here now)
- `backend/app/db/jobs.py` (modified — becomes a thin wrapper)
- `backend/app/db/cli.py` (modified — handle the conflict case)
