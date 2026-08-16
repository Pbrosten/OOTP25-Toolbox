# 0070 — Prospect Pipeline frontend view

- **Tag:** feat
- **Status:** Closed
- **Depends on:** [0069](0069-prospect-query-layer-api.md)
- **Blocks:** —

## 1. Problem

[0069](0069-prospect-query-layer-api.md) exposes the prospect data over the
API; nothing renders it. `docs/improvements/expanded-functionality.md`
suggests a `FARM SYSTEM › Prospect Pipeline` IA placement — this ticket is
that view, mirroring how [0064](0064-roster-depth-chart-frontend.md) built
the org depth-chart view on top of 0063's API.

## 2. Design choices

No new design questions beyond what 0043 already resolved — this is
presentation of already-defined data (FV grade, surplus value, star odds,
MLB-promotion-ready flag, trend direction). Layout/component-structure
choices deferred to implementation time, same as 0064's approach.

## 3. Approach

- New route/view under the Farm System IA area, listing prospects
  filterable by org/level/position, sortable by FV grade or surplus value.
- Reuse existing display conventions: 20-80 grade bars
  (`PercentileBar.vue`-adjacent components already used elsewhere for
  20-80 scale display), trend indicators from 0052's
  `DevelopmentTrends`-style display, and 0057's surplus-value display
  conventions for the dollar figures.
- Promotion-ready prospects surfaced distinctly (matches the source doc's
  "surfacing prospects ready for promotion" ask).

**Files involved:**
- `frontend/src/views/ProspectPipelinePicker.vue` (new) — org picker,
  mirrors `TeamPicker.vue`'s fetch-teams/select pattern rather than
  extending that component in place (avoids changing its existing
  auto-navigate-on-select behavior for the depth-chart flow).
- `frontend/src/views/ProspectPipeline.vue` (new) — the main view for
  `/teams/:id/prospects`: fetches `GET /api/prospects?team_id=...` (org-
  scoped, per 0069's verified ~1.6s-vs-~46s finding — this view never
  calls the endpoint unfiltered) plus `GET /api/teams` for the org's
  display name. Single sortable/filterable table (not level-tabbed like
  `TeamDepthChart.vue` — sorting by FV/surplus value across the whole org
  is the point, per 0043's "viable trade assets" framing) with level/
  position filters, FV grade badge (tiered color, no "red" tier --
  even a low-ceiling prospect is a real asset, not a liability),
  `formatMoney` compact-currency convention reused from `SurplusValue.vue`
  (0057), trend badges reusing `DevelopmentTrends.vue`'s teal/red color
  language (0052), and the same `ArrowUpCircleIcon` "ready" marker
  `TeamDepthChart.vue` uses for `is_promotion_candidate`, here for
  `mlb_promotion_ready`. Unavailable-value prospects (missing rating data
  only, as of 0068's post-close correction removing the RP exclusion —
  see below) always sort last, mirroring `TeamDepthChart.vue`'s null-WAR
  handling (ticket 0064).
- `frontend/src/router/index.ts` (modified) — registers `/prospects` and
  `/teams/:id/prospects`.
- `frontend/src/views/LandingPage.vue` (modified) — adds a "Prospect
  Pipeline" tool card.

**Superseded:** this ticket originally noted a known limitation here about
RP-role prospects always showing "Not available" indistinguishably from a
data-missing case. Moot as of 0068's post-close correction (user request)
removing the RP exclusion entirely — every pitcher now gets a real FV/
value, so there's no longer a role-based "not available" case to confuse
with a data-missing one.

## 4. Verification

No browser automation tool was available this session (Claude in Chrome
extension not connected) to visually confirm rendering/interaction --
disclosed rather than assumed working. What *was* verified:
- Both new `.vue` files compile cleanly through Vite's dev-server SFC
  transform (HTTP 200, no compile errors) via direct request to
  `localhost:5173/src/views/ProspectPipeline*.vue`.
- `npm run build`'s `vue-tsc` type-check step fails, but on pre-existing,
  unrelated `@/`-path-alias resolution errors affecting *every* `@/`-
  imported file in the whole project (confirmed: `App.vue`, `main.ts`,
  every existing view) -- not something introduced by this ticket's files.
- The running dev server's Vite proxy (`localhost:5173/api/prospects` and
  `/api/teams`) correctly forwards to the backend and returns the exact
  shape the component consumes, confirmed against the real `TEST.lg` save
  (BOS/team_id=4, 214 prospects).
- `/prospects` and `/teams/4/prospects` both serve the SPA shell (200).

Recommend the user do a quick visual pass in a browser before closing,
given the above gap.
