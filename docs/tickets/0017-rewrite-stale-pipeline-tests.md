# 0017 — Rewrite or remove 16 stale pipeline tests

- **Tag:** chore
- **Status:** Closed
- **Depends on:** —
- **Blocks:** —

## 1. Problem

`backend/tests/db/` currently runs at 16 failed / 24 passed
(`test_connection.py` 2, `test_migration.py` 3, `test_projection.py` 2,
`test_stagging.py` 3, `test_update.py` 6). Every failure targets a
**removed** pre-MariaDB implementation (SQLite-backed staging,
`executescript()`, `inject_db_path()`/`STAGGING_DB_PATH` templating, a
tuple-of-two-lists `check_new_heaps()` return shape, direct
`db.executemany()`/`db.commit()` instead of cursor-scoped calls) — the
source was migrated to the current pymysql/two-database design but these
tests weren't updated alongside it. None of the 16 catch a real defect;
full reasoning per test is in
[docs/wiki/Ingestion-Pipeline.md §10](../wiki/Ingestion-Pipeline.md#10-test-coverage-status).

A perpetually red test suite for this module trains contributors to ignore
failures here, which is exactly the condition under which a real regression
would go unnoticed. It also means the pipeline's actual current behavior —
everything documented in `docs/wiki/Ingestion-Pipeline.md` — has no
regression coverage at all.

## 2. Design choices

Chosen approach, no real alternatives considered: rewrite each test against
the current API, mirroring the working patterns already in
`test_service.py`/`test_jobs.py` (which correctly mock
`get_db`/`close_db`/cursor context managers), rather than deleting outright
— the coverage these tests were originally meant to provide (staging load,
migration execution, projection batching) is still relevant to today's
implementation, it's just asserting against the wrong shape.

- **Sequencing.** Natural to pair with whichever of
  [0007](0007-persist-processed-heaps.md)–[0016](0016-update-db-row-count-visibility.md)
  gets picked up first, to lock in the *new* correct behavior with a test
  rather than writing tests for code about to change again. Not a hard
  dependency — this ticket can proceed standalone against current behavior
  if nothing else lands first.

## 3. Approach

- `test_connection.py`: rewrite the 2 failing tests against
  `get_db()`/`close_db()`'s actual pymysql-based implementation (drop
  SQLite-specific assumptions).
- `test_migration.py`: rewrite the 3 `inject_db_path` tests to test
  `inject_heap_date()` (the function that actually exists today) instead.
- `test_projection.py`: rewrite the 2 `update_projection_batches` tests
  against the current cursor-context-manager-based commit flow.
- `test_stagging.py`: rewrite the 3 tests — `check_new_heaps()`'s actual
  `(path, is_short)` tuple-list return shape, `sql_dump_to_staging()`'s
  actual line-buffered execution.
- `test_update.py`: rewrite the 6 tests against `db.cursor()`-scoped
  execute/commit calls instead of direct `db.executemany()`/`db.commit()`.
- Delete any test whose original target function no longer exists at all
  (e.g. `inject_db_path`) rather than force-fitting it to a same-named but
  differently-behaved current function.

**Files involved:**
- `backend/tests/db/test_connection.py` (modified)
- `backend/tests/db/test_migration.py` (modified)
- `backend/tests/db/test_projection.py` (modified)
- `backend/tests/db/test_stagging.py` (modified)
- `backend/tests/db/test_update.py` (modified)
