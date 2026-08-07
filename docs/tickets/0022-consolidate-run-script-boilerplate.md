# 0022 — Consolidate repeated run-script/rollback/commit boilerplate

- **Tag:** refactor
- **Status:** Closed
- **Depends on:** —
- **Blocks:** —

## 1. Problem

`run_migration_short`, `run_migration_long`, and `fetch_projection_inputs`
(`backend/app/db/update.py:97-156`) are three near-identical blocks: open a
`.sql` resource, split on `;`, execute each statement, `rollback()` + log +
re-raise on exception or `commit()` on success. Copy-pasted three times.

## 2. Design choices

Chosen approach, no real alternatives considered: factor into one shared
helper. The three call sites differ only in (a) script path, (b) whether
`{{HEAP_DATE}}` gets injected, and (c) whether the cursor's result rows are
returned to the caller — all three are easy to parameterize.

## 3. Approach

- Add `_run_sql_script(script_path, db, heap_date=None, fetch=False)` to
  `backend/app/db/update.py`:
  - Opens the resource, reads it, optionally runs `inject_heap_date()` if
    `heap_date` is given.
  - Opens `db.cursor()`, executes each `;`-split statement, `rollback()` +
    log + re-raise on exception, `commit()` on success — all inside the
    `with` block.
  - If `fetch=True`, fetches and returns `[dict(row) for row in
    cursor.fetchall()]` from inside the same `with` block (folds in
    [0021](0021-fetch-projection-inputs-cursor-scope.md)'s fix directly
    rather than as a separate pass).
- Reimplement `run_migration_short`, `run_migration_long`, and
  `fetch_projection_inputs` as thin callers of `_run_sql_script(...)`.

**Files involved:**
- `backend/app/db/update.py` (modified)
