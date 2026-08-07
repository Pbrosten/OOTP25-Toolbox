# 0007 — Track processed heaps so update-db only ingests what's new

- **Tag:** feat
- **Status:** Closed
- **Depends on:** —
- **Blocks:** —

## 1. Problem

`check_new_heaps()` (`backend/app/db/staging.py:47`) lists every heap
directory under `DUMP_PATH` and returns all of them, on every call — there's
no persisted record of which heaps have already been processed. A save with
3 years of history (36 monthly + 3 yearly heaps) reprocesses all 39 heaps —
full staging reload, full migration SQL, full `multiprocessing.Pool(cpu_count())`
batter-projection pass over every player — on *every* `update-db`
invocation, including ones where nothing on disk changed. Cost scales with
total heap count ever placed under `DUMP_PATH`, not with what's new.

This also makes `docs/wiki/Updating-the-Database.md`'s current claim
("`update-db` is safe to re-run — it only processes heaps it hasn't seen
before") inaccurate; that page should be corrected regardless of whether
this ticket is picked up.

As dump history grows, `update-db` run time grows unboundedly even when the
operator only wants to ingest this month's new heap. At some save-history
size this turns a few-second operation into a multi-minute one, defeating
the purpose of the async job work in [0004](0004-async-update-db-job.md).

## 2. Design choices

- **Tracking mechanism.** Options considered: (a) a new `processed_heaps`
  table in `ootp` (heap identity + processed timestamp), written after a
  heap's migration commits successfully; (b) inferring "already processed"
  from existing data (e.g. does `players_rating` already have a row for this
  `rating_date`). **Chosen: (a)**, because it's explicit and doesn't require
  every future heap type to have an unambiguous "have we seen this" query
  against domain tables — the ratings-date check in particular would break
  for long heaps, which don't write a dated ratings row.
- **Heap identity.** Use `(year, month, is_short)` as the natural key (matches
  what `check_new_heaps()` already parses from the directory name), not the
  raw path — the directory name already uniquely encodes heap identity and
  is decoupled from wherever `DUMP_PATH` happens to point.
- **Outstanding:** what "already processed" means if the *dump file
  contents* change without the directory name changing (unlikely given
  OOTP's export naming, but stated here as an explicit non-goal — this
  ticket does not detect or handle content-only changes to an
  already-processed heap directory).

## 3. Approach

- Add a `processed_heaps` table to `schema.sql`:
  `(year SMALLINT, month SMALLINT, is_short BOOLEAN, processed_at DATETIME,
  PRIMARY KEY (year, month, is_short))`.
- `check_new_heaps()` (`staging.py`) queries this table and filters the
  on-disk heap list against it before returning, instead of returning
  everything unconditionally.
- `process_single_heap()` / `service.update_database()` (`update.py`) insert
  a row into `processed_heaps` immediately after a heap's migration commits
  successfully, so a crash mid-heap doesn't mark it processed.
- Correct `docs/wiki/Updating-the-Database.md`'s re-run-safety claim to match
  actual (now-correct) behavior.

**Files involved:**
- `backend/app/db/staging.py` (modified — `check_new_heaps()`)
- `backend/app/db/update.py` (modified — mark-processed write)
- `backend/app/db/sql_scripts/schema.sql` (modified — new table)
- `docs/wiki/Updating-the-Database.md` (modified — doc correction)
