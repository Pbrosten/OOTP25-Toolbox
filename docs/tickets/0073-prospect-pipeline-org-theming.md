# 0073 — Org color theming for the Prospect Pipeline page

- **Tag:** feat
- **Status:** Closed
- **Depends on:** [0070](0070-prospect-pipeline-frontend.md)
- **Blocks:** —

## 1. Problem

Filed from a user report while reviewing the Prospect Pipeline: selecting
an org on `ProspectPipeline.vue` shows a fixed teal header, unlike
`TeamDepthChart.vue` (ticket 0064), which themes its header with the
selected MLB team's real colors (`teams.background_color`/`text_color`,
applied via a `teamColors` computed + inline CSS custom properties). The
Prospect Pipeline is the same "pick an org, see org-scoped data" shape as
the depth chart and should carry the same theming for visual consistency
between the two Farm-System-adjacent views.

## 2. Design choices

- **Resolved — color data source: extend `GET /api/teams`.** The only
  real open question this ticket had. `GET /api/prospects` doesn't return
  `background_color`/`text_color`, and `ProspectPipeline.vue` already
  fetches `GET /api/teams` separately just to resolve the org's display
  name — adding the two color columns to that route's existing `SELECT`
  (`app/api/teams.py::get_mlb_teams`) needed no new endpoint and no
  wasted depth-chart fetch just for two columns, exactly as the ticket's
  own filing already reasoned. Purely additive to the response shape, so
  no risk to the existing depth-chart team picker that also consumes this
  route.

## 3. Approach

- `backend/app/api/teams.py::get_mlb_teams`: added `background_color,
  text_color` to the `SELECT`.
- `backend/docs/openai.yaml`: documented the two new response fields.
- `frontend/src/views/ProspectPipeline.vue`: replaced the `teamName` ref
  with a `team` ref holding the full matched team object, plus a
  `teamName` computed and a `teamColors` computed
  (`--team-bg`/`--team-text` CSS custom properties) — the exact same
  shape and fallback colors (`#0f766e`/`#ffffff`) as
  `TeamDepthChart.vue`'s own `teamColors`. Applied via `:style="teamColors"`
  on the page wrapper and `style="background-color: var(--team-bg); ..."`
  on the header, replacing the previous fixed `bg-teal-700 text-white`.

**Verified against real data** (backend container restarted to pick up
the route change):
- `GET /api/teams` now returns Philadelphia's real colors
  (`background_color: "#E81828"`, `text_color: "#003278"`) alongside the
  existing fields.
- Confirmed identical through the frontend dev server's proxy
  (`localhost:5173/api/teams`).
- `TeamDepthChart.vue`'s own depth-chart route unaffected (still 200,
  additive schema change only).
- `ProspectPipeline.vue` compiles cleanly through Vite's SFC transform (no
  browser tool available this session to visually confirm rendering —
  same disclosed gap as 0070/0071).
- Full backend suite: 173/173 passing, no regressions.

**Files involved:**
- `backend/app/api/teams.py` (modified)
- `backend/docs/openai.yaml` (modified)
- `frontend/src/views/ProspectPipeline.vue` (modified)

## 4. Additional fix (same session, user report): international-complex
signees mislabeled "MLB" and showing a broken Career Stats section

While reviewing the theming change, the user found a real case: Cris
Ortega (age 17, Texas Rangers) showed `Level: MLB` in the Prospect
Pipeline and a "Failed to load batting stats" error on his player page.

**Root cause (confirmed against real data):** Ortega is `player_id`
138746, parked at `team_id = 28` (the real Rangers MLB team, `level = 1`,
a real city) with `players_service_time.is_active = 0` and
`is_on_secondary = 0`. Same underlying data quirk `get_org_depth_chart.sql`
already handles (ticket 0064's post-close correction): a young
international signee has no real "International Complex" team_id to be
rostered on in this save, so OOTP parks him directly under his org's MLB
team_id with no real active/secondary roster flag set. `get_prospects.sql`
had no equivalent check, so he read as a real level-1 rookie; his player
page tried to load MLB career batting stats that don't exist yet (he's
never recorded a season), which 404'd and surfaced as a generic error.

**Fix:**
- `backend/app/db/sql_scripts/api/get_prospects.sql`: a player's
  *displayed* `level` is now overridden to a synthetic `0` when
  `teams.level = 1` and both `is_active`/`is_on_secondary` are false/NULL
  — never a real `teams.level` value (confirmed: only NULL/1/2/3/4/5/6
  ever appear). Restructured into two sequential CTEs
  (`prospect_candidates` → `prospects`) so the `level` query-param filter
  applies to this computed value too, not just the raw column — `?level=0`
  now finds these players. The prospect *definition* itself (who counts as
  a prospect at all) is unchanged, still keyed off the raw `teams.level`.
- `frontend/src/views/ProspectPipeline.vue`: added `0: "Int'l Complex"` to
  `LEVEL_LABELS`, sorted last in `LEVEL_ORDER`. Also fixed a real bug this
  introduced: the level filter's `if (levelFilter.value)` truthy check
  silently no-op'd when `0` was selected (falsy, indistinguishable from
  the `''` "All Levels" default) — changed to `!== ''`.
- `backend/app/db/sql_scripts/api/get_player_details.sql`: added an
  `is_international_complex` boolean (same `is_active`/`is_on_secondary`
  logic, LEFT JOIN `players_service_time`).
- `frontend/src/components/PlayerDetails.vue`: skips fetching *and*
  rendering both Career Batting Stats and Career Pitching Stats entirely
  when `is_international_complex` is true, rather than surfacing a
  "Failed to load ... stats" error for a state that isn't actually an
  error (no career rows exist yet for these players).

**Verified against real data:**
- `GET /api/prospects?team_id=28` (Rangers): Cris Ortega now shows
  `"level": 0`; 18 of the org's prospects are int'l-complex signees
  (previously miscounted as MLB).
- `GET /api/prospects?team_id=28&level=0` returns exactly those 18;
  `?level=1` correctly drops to the real 10 MLB-level prospects.
- `GET /api/prospects/138746` now includes `"mlb_promotion_ready": false`
  (previously omitted, since the old raw `level = 1` incorrectly gated it
  off).
- `GET /api/players/138746/details` returns
  `"is_international_complex": 1`; a real veteran (Carlos Rodón) returns
  `0`. `GET /api/players/138746/career/batting` still genuinely 404s (no
  rows exist), confirming the frontend fix — not the backend — is what
  stops that from surfacing as a visible error.
- Full backend suite: 173/173 passing. Both modified `.vue` files compile
  cleanly through Vite's SFC transform.
