# 0013 — Re-enable the staging DB reset before each load

- **Tag:** chore
- **Status:** Closed
- **Depends on:** —
- **Blocks:** —

## 1. Problem

The `DROP TABLE`/`SET FOREIGN_KEY_CHECKS` staging-reset block in
`backend/app/db/staging.py::connect_staging_db()` (lines 36-43) is fully
commented out. Correctness currently depends entirely on each dump file
containing its own `DROP TABLE`/`CREATE TABLE` (standard `mysqldump`
per-table export behavior) — there are no sample dump fixtures in this repo
to confirm that holds for every table OOTP exports. If any included dump
file omits its own reset, staging tables silently accumulate cross-heap
data, contaminating the migration JOINs for that table.

Silent data corruption if the assumption ever breaks for one table — hard to
detect since `INSERT IGNORE` on the `ootp` side would mask most symptoms.

## 2. Design choices

- **Re-enable vs. confirm-then-delete.** Options considered: (a) confirm
  (with a real OOTP dump export) that every ingested file self-resets and
  delete the dead code with a comment explaining the invariant it relies on;
  (b) just re-enable the reset. **Chosen: (b)** — the reset is cheap
  (`SHOW TABLES` + one `DROP TABLE IF EXISTS` per table, once per heap,
  against a handful of staging tables) and removes the silent-corruption
  risk unconditionally, without needing to first prove the invariant holds
  for every table OOTP exports (including ones not currently covered by any
  test fixture). Confirming the invariant would only justify *not* paying an
  already-small cost, which isn't worth the verification effort.

## 3. Approach

- Uncomment the reset block in `connect_staging_db()`
  (`backend/app/db/staging.py:36-43`) as-is — no logic changes needed, it
  was already correct, just disabled.
- Add a regression test (can be paired with
  [0017](0017-rewrite-stale-pipeline-tests.md)'s test rewrite) asserting
  `connect_staging_db()` issues the `DROP TABLE`/`FOREIGN_KEY_CHECKS`
  statements, since this is exactly the kind of change that's easy to
  silently re-disable later without a test catching it.

**Files involved:**
- `backend/app/db/staging.py` (modified — uncomment lines 36-43)
- `backend/tests/db/test_stagging.py` (modified — add coverage)
