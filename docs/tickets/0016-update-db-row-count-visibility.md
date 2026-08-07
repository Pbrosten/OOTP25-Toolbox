# 0016 — Report row counts actually written by update-db, not just heaps attempted

- **Tag:** feat
- **Status:** Closed
- **Depends on:** —
- **Blocks:** —

## 1. Problem

Nothing in the pipeline captures affected-row counts.
`service.update_database()`'s return payload
(`{"status": "ok", "heaps_processed": N, "long_heaps": X, "short_heaps": Y}`,
`backend/app/db/service.py:64-69`) reports heaps *attempted*, not rows
actually written. Combined with `INSERT IGNORE` swallowing FK violations
(documented in `docs/wiki/Troubleshooting.md`'s "short heap against an empty
players table silently inserts nothing" gotcha), an operator can get a
`status: "ok"` / job `status: "succeeded"` result with zero net new data and
no way to tell from the API response alone.

## 2. Design choices

Chosen approach, no real alternatives considered: use `cursor.rowcount`
after each `INSERT`/`UPDATE` statement, which pymysql already exposes for
free — no need for a separate `SELECT COUNT(*)` before/after comparison.

- **Outstanding:** whether to break counts down per-table (e.g.
  `ratings_inserted`, `batting_inserted`, `fielding_inserted`) or just a
  couple of coarse buckets (`ratings_inserted`, `players_updated`,
  `projections_inserted`) is left to the implementer — the README's
  suggested three-bucket shape is a reasonable default, but isn't binding.

## 3. Approach

- `run_migration_short`/`run_migration_long`
  (`backend/app/db/update.py`) accumulate `cursor.rowcount` per executed
  statement (skip/ignore negative rowcounts from non-DML statements) and
  return a counts dict instead of (or alongside) nothing.
- `process_single_heap()` aggregates per-heap counts and returns them instead
  of `None`.
- `service.update_database()` sums counts across all processed heaps into
  its return dict, e.g.
  `{"status": "ok", "heaps_processed": N, "ratings_inserted": N,
  "players_updated": N, "projections_inserted": N}`.
- Update `backend/docs/openai.yaml`'s `update-db`/`jobs` response schema to
  document the new fields.

**Files involved:**
- `backend/app/db/update.py` (modified)
- `backend/app/db/service.py` (modified)
- `backend/docs/openai.yaml` (modified)
