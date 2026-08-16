# 0077 — Leaderboard frontend view

- **Tag:** feat
- **Status:** Closed
- **Depends on:** [0076](0076-leaderboard-query-layer-api.md)
- **Blocks:** —

## 1. Problem

[0076](0076-leaderboard-query-layer-api.md) exposes the leaderboard over
the API; nothing renders it.

## 2. Design choices

Resolved in 0074: a new dedicated view/route, not a mode toggle grafted
onto `ProspectPipeline.vue` — the three-curated-section response shape is
different enough from the org-scoped flat table that it warrants its own
component, same reasoning 0070 used for building a dedicated view rather
than repurposing `TeamDepthChart.vue`.

## 3. Approach

- `frontend/src/views/ProspectLeaderboard.vue` (new), route
  `/prospects/leaderboard`: fetches `GET /api/prospects?leaderboard=1`
  with `position`/`level`/`page`/`page_size` query params, refetching
  (via `watch`) whenever a filter or the page changes -- filter changes
  reset to page 1. Three sections:
  - **Overall** — paginated table (rank, player, pos, age, level, team,
    FV, surplus value, star odds) with Previous/Next controls and a
    "Page X of Y" indicator, driven by the API's `page`/`page_size`/
    `total`. No trend column -- leaderboard mode doesn't compute trend
    (ticket 0076's Design choices).
  - **Top 10 by Position** / **Top 10 by Level** — a responsive grid of
    cards, one per group (ordered via `POSITION_ORDER`/`LEVEL_ORDER`,
    same constants `ProspectPipeline.vue` already established, duplicated
    per that component's own per-file convention), each a ranked list of
    up to 10 (rank, name, FV badge).
  - Reused as-is from `ProspectPipeline.vue`: `LEVEL_LABELS`/
    `LEVEL_ORDER`/`POSITION_ORDER`, `formatMoney`/`formatPercent`,
    `fvClass` (FV badge tiering), `riskTagTitle` (ticket 0072's tag
    tooltip), the `ArrowUpCircleIcon` `mlb_promotion_ready` marker.
- `frontend/src/router/index.ts` (modified) — registers
  `/prospects/leaderboard`.
- `frontend/src/views/ProspectPipelinePicker.vue` (modified) — adds a
  "View league-wide leaderboard →" link below the org picker (a separate
  link, not a select option, since it's an unfiltered view rather than
  another org choice).

**Verification:** No browser tool available this session (same disclosed
gap as 0070/0071/0073) to visually confirm rendering/interaction. What
*was* verified:
- `ProspectLeaderboard.vue`, `ProspectPipelinePicker.vue`, and
  `router/index.ts` all compile cleanly through Vite's dev-server SFC
  transform (HTTP 200, no compile errors).
- `GET /api/prospects?leaderboard=1&page=1&page_size=50` through the
  frontend's own proxy returns the exact shape the component consumes,
  confirmed against the real save: 2,240 total, 50 results on page 1, all
  9 real positions and 6 real levels (including "0" for Int'l Complex)
  present in the section objects.
- `/prospects/leaderboard` serves the SPA shell (200).

Recommend a quick visual pass in a browser before closing, same as prior
frontend tickets in this epic.

**Files involved:**
- `frontend/src/views/ProspectLeaderboard.vue` (new)
- `frontend/src/router/index.ts` (modified)
- `frontend/src/views/ProspectPipelinePicker.vue` (modified)

## 4. Follow-up (same session, user request): org instead of team, page
size 20

- **Org, not immediate affiliate team.** `team_abbr` (the player's own
  roster team -- for a minor-leaguer, his specific affiliate, e.g. "BEL")
  isn't what a GM scanning a league-wide board wants; they want the
  parent organization ("MIA"). New `org_abbr` column in
  `get_prospect_leaderboard.sql`: self-joins `teams` again, resolving to
  `parent_team_id` unless it's `0` (confirmed against real data: a
  level-1 team's own `parent_team_id` is always `0`, never NULL, meaning
  "no parent -- this team IS the org," in which case the team's own
  `team_id` is used instead). Threaded through `_leaderboard_entry()` in
  `app/api/prospects.py` and displayed in all three sections (Overall
  table's "Org" column, plus the Top-10-by-Position/Level card lists,
  which previously showed no team/org info at all). `team_abbr` is still
  returned too, just no longer what the frontend displays.
- **Page size 20, not 50** (user request) -- `LEADERBOARD_DEFAULT_PAGE_SIZE`
  in `prospects.py` and the frontend's matching `pageSize` constant.

**Verified against real data** (backend container restarted):
- `page_size: 20` in the response, 20 results returned.
- Willie Arguello (level 4, A/High-A): `team_abbr: "BEL"` (his actual
  affiliate) vs. `org_abbr: "MIA"` (his real parent org) -- confirms the
  two are genuinely different values, not just a rename.
  Level-1 players (e.g. Jonathan Flores) correctly show `team_abbr ==
  org_abbr`, since at level 1 the team already is the org.
- `top_by_position`/`top_by_level` entries now carry `org_abbr` too.
- Full backend suite: 209/209 passing (fixture/tests updated for the new
  column and page-size default).

**Files involved (this follow-up):**
- `backend/app/db/sql_scripts/api/get_prospect_leaderboard.sql` (modified)
- `backend/app/api/prospects.py` (modified)
- `backend/docs/openai.yaml` (modified)
- `backend/tests/api/test_prospects.py` (modified)
- `frontend/src/views/ProspectLeaderboard.vue` (modified)
