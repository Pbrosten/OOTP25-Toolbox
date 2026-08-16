# 0076 — Leaderboard query layer + API

- **Tag:** feat
- **Status:** Closed
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

## 4. Implementation

- `backend/app/db/sql_scripts/api/get_prospect_leaderboard.sql`: mirrors
  `get_prospects.sql`'s two-CTE prospect-definition filter (including the
  level=0 "Int'l Complex" override, ticket 0073) but INNER JOINs
  `players_prospect_value` instead of live-computing -- a prospect with no
  persisted row (0075's known gap, or a genuinely missing calc) is simply
  absent from the result set rather than shown `available: false`. No
  `player_id` param (this query is always a list). Ordered `fv DESC,
  surplus_value DESC`.
- `backend/app/api/prospects.py`: `get_prospects()` branches on
  `request.args.get("leaderboard")` before touching the org-scoped path at
  all -- existing behavior fully unchanged when absent. New
  `_prospect_leaderboard()` runs the query once, applies the existing
  `EXCLUDED_FV` filter (ticket 0072's FV-30 exclusion, kept consistent
  across both modes), and slices the single fv-sorted result set three
  ways in Python: `top_overall` via plain list slicing for pagination,
  `top_by_position`/`top_by_level` by taking the first
  `LEADERBOARD_SECTION_SIZE` (10) rows encountered per group -- valid
  because the group subsets of an already-globally-sorted list preserve
  that sort order, so no separate SQL queries or re-sorting needed. New
  `_leaderboard_entry()` reshapes each row into the same identity/value
  shape the org-scoped mode's rows use (for frontend reuse, ticket 0077),
  recomputing `mlb_promotion_ready` from `current_fv` at read time (0075
  deliberately doesn't persist it, being level-dependent).
- `backend/docs/openai.yaml`: documented the three new query params
  (`leaderboard`, `page`, `page_size`) and the leaderboard response shape
  as a `oneOf` alternative to the existing flat-array schema.
- 12 new tests in `backend/tests/api/test_prospects.py`: response shape,
  section grouping/ranking, the 10-per-group cap, pagination (including
  default page size), FV-30 exclusion, `mlb_promotion_ready` gating, filter
  passthrough, and confirming no per-player trend queries run in this mode.

**Verified against real data** (backend container restarted to pick up
the change):
- `GET /api/prospects?leaderboard=1`: **0.27s**, down from 0069's ~46s
  unfiltered baseline -- confirms 0075's persistence solved the
  performance problem this whole sub-epic exists for. 2,240 total
  league-wide prospects (post FV-30 exclusion); top result a real FV 80
  with a "-" risk tag and correctly risk-discounted surplus value
  ($136.5M, the FV-70-fallback $195M base × the 0.70 "-" modifier);
  `top_by_position` covers all 9 real positions, each capped at 10;
  `top_by_level` covers every real level including "0" (Int'l Complex).
- `?leaderboard=1&position=SS`: 0.06s, 243 total, every result actually SS.
- `?leaderboard=1&page=2&page_size=5`: correct second page of 5 distinct
  players.
- Full backend suite: 209/209 passing.

**Files involved:**
- `backend/app/db/sql_scripts/api/get_prospect_leaderboard.sql` (new)
- `backend/app/api/prospects.py` (modified)
- `backend/docs/openai.yaml` (modified)
- `backend/tests/api/test_prospects.py` (modified)
