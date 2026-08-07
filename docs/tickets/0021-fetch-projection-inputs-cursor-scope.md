# 0021 — Fetch projection inputs inside the cursor's with block

- **Tag:** refactor
- **Status:** Closed
- **Depends on:** —
- **Blocks:** —

## 1. Problem

In `fetch_projection_inputs()` (`backend/app/db/update.py:136-156`),
`return [dict(row) for row in cursor.fetchall()]` is dedented outside the
`with db.cursor() as cursor:` block (line 144). This happens to work today
because pymysql's `Cursor.close()` doesn't clear the already-buffered
`self._rows` — but it relies on non-contractual internal cursor state rather
than fetching inside the `with` block as the code visually suggests.

## 2. Design choices

Chosen approach, no real alternatives considered: move the fetch inside the
`with` block. Purely a readability/robustness fix, no behavior change.

## 3. Approach

- Move `return [dict(row) for row in cursor.fetchall()]` inside the
  `with db.cursor() as cursor:` block in `fetch_projection_inputs()`, after
  the statement-execution loop, instead of after the block exits.
- Natural to combine with [0022](0022-consolidate-run-script-boilerplate.md),
  which touches the same function.

**Files involved:**
- `backend/app/db/update.py` (modified)
