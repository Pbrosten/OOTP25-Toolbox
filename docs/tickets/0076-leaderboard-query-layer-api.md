# 0076 — Leaderboard query layer + API

- **Tag:** feat
- **Status:** Open
- **Depends on:** [0075](0075-persist-prospect-value-per-heap.md)
- **Blocks:** [0077](0077-leaderboard-frontend-view.md)

## 1. Problem

[0075](0075-persist-prospect-value-per-heap.md) persists FV/value per
heap; nothing reads it yet. `GET /api/prospects` still only supports the
org-scoped, live-computed path (0069).

## 2. Design choices

Resolved in 0074, restated at implementation-detail level:

- **`?leaderboard=1` query param on the existing `GET /api/prospects`
  route**, not a new URL — an explicit trigger rather than inferring
  leaderboard mode from `team_id` being absent (which today already means
  "every prospect, flat array" and shouldn't silently change shape).
  `team_id`/`position`/`level` stay meaningful as additional filters in
  leaderboard mode too (e.g. `?leaderboard=1&position=SS`).
- **Response is three curated sections, not a flat array**: `top_overall`
  (paginated), `top_by_position` (top 10 each), `top_by_level` (top 10
  each) — a structurally different shape from the org-scoped mode's flat
  list, returned from the same route under the new param.
- **Reads `players_prospect_value` joined against current
  `players`/`teams`**, same prospect-definition filter 0069's live path
  already applies (age < 26, non-MLB or zero-service rookie, excluding
  level 5/team_id 999) — this is where "is he still actually a prospect
  today" gets re-validated, not from anything stored per-heap (see 0075's
  Design choices). `current_fv >= 40` recomputes `mlb_promotion_ready` at
  read time, matching 0075's decision not to persist it.
- **Latest-rating-per-player only.** The leaderboard ranks each player
  once, off their latest heap's persisted row — not every historical
  heap's row sitting in `players_prospect_value`.
- **Pagination on `top_overall` only**: `page`/`page_size` params
  (default ~50), real `LIMIT`/`OFFSET` at the SQL level now that the read
  is a plain indexed query. `top_by_position`/`top_by_level` are
  fixed-size (10 each), no pagination needed.
- **Ranked by `fv` descending, `surplus_value` descending as tiebreak**
  within each section.

## 3. Approach

- New SQL, `backend/app/db/sql_scripts/api/get_prospect_leaderboard.sql`:
  latest-rating CTE (same shape as `get_prospects.sql`'s) joined to
  `players_prospect_value`, filtered by the current prospect definition
  plus any `team_id`/`position`/`level` params, ordered by `fv DESC,
  surplus_value DESC`. Three variants (overall/by-position/by-level) —
  either three separate queries or one query the route slices three ways
  in Python; exact shape decided at implementation time based on what
  reads cleanest.
- `backend/app/api/prospects.py`: `get_prospects()` branches on
  `request.args.get("leaderboard")` — existing org-scoped behavior
  unchanged when absent; new leaderboard branch runs the query above and
  shapes the three-section response.
- `backend/docs/openai.yaml`: document the new param and the
  leaderboard-mode response shape (likely as an alternate schema on the
  same path, since the shape genuinely differs from the org-scoped mode).
- Tests: `backend/tests/api/test_prospects.py` — leaderboard-mode
  response shape, pagination, section ranking, filter passthrough.

**Verification note:** re-measure the leaderboard's actual response time
against the real save once implemented — 0075's persistence is what's
supposed to fix the ~46s finding from 0069, so confirm it actually lands
in the sub-second-to-low-single-digit-second range before calling this
done, the same way every other ticket in this epic has verified against
live data rather than assuming.

**Files involved:**
- `backend/app/db/sql_scripts/api/get_prospect_leaderboard.sql` (new)
- `backend/app/api/prospects.py` (modified)
- `backend/docs/openai.yaml` (modified)
- `backend/tests/api/test_prospects.py` (modified)
