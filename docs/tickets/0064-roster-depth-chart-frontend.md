# 0064 — Roster depth-chart frontend view

- **Tag:** feat
- **Status:** Open
- **Depends on:** [0063](0063-roster-depth-chart-query-api.md)
- **Blocks:** —

## 1. Problem

[0063](0063-roster-depth-chart-query-api.md) exposes an org's full
depth chart (MLB roster + AAA/AA/A/Rookie affiliates, grouped by
position/role and ranked by WAR) via API; nothing surfaces it in the UI
yet. [0039](0039-roster-optimization-org-depth.md)'s source doc calls
for a `ROSTER › Roster Optimization / Organizational Depth` page.

## 2. Design choices

- **New top-level view, not a tab on an existing player/team page.**
  This is org-scoped (a whole team's roster tree), not player-scoped, so
  it doesn't fit under `PlayerProfile.vue`. **Chosen:** a new
  `frontend/src/views/`, matching how `AdminPanel.vue`/`PlayerSearch.vue`
  are their own top-level views, routed at (e.g.) `/teams/:id/depth-chart`.
- **Layout: one table per level, position (or SP/RP) as row groups within
  it.** Mirrors 0063's response shape (`{level: {group: [players]}}`)
  directly rather than re-shaping it client-side — matches this
  project's established pattern of the frontend rendering whatever shape
  the backend already returns (e.g. 0037's note that a cohort-scoping
  change needed no frontend change at all because the response shape
  didn't change; here the reverse holds — the frontend layout should
  follow the response shape 0063 defines).
- **Team selection: reuse `PlayerSearch.vue`'s pattern, not a new
  picker.** No "current team"/session concept exists anywhere in the app
  yet (same gap [0038](0038-gm-command-center.md) flagged) — this ticket
  doesn't invent one. **Chosen:** a simple team picker (dropdown or
  search-like input over the ~30 MLB teams, `level = 1`) that navigates to
  `/teams/:id/depth-chart`, no persisted "my team" state.
- **Outstanding:** none — this is a straightforward consumer of 0063's
  already-shaped response.

## 3. Approach

- `frontend/src/views/TeamDepthChart.vue` (new): fetches
  `/api/teams/<id>/depth-chart` on mount (`onMounted`, keyed by the route
  param the same way [0061](0061-refetch-player-data-on-route-param-change.md)'s
  `<router-view :key>` fix already ensures a remount on navigation between
  different team ids), renders one section per level (MLB/AAA/AA/A/
  Rookie, in that order), each with position/role-group sub-tables listing
  players sorted by WAR (already sorted by the API).
- `frontend/src/router/index.ts`: add the `/teams/:id/depth-chart` route.
- A lightweight team picker (new small component, or inlined into
  `TeamDepthChart.vue` if simple enough) listing MLB (`level = 1`) teams —
  reuse `GET /api/teams` if it exists, or add a minimal listing endpoint
  to `app/api/teams.py` (from 0063) if it doesn't.
- Verify against the live dev stack (`npm run dev`, established pattern):
  load a real org's depth chart, confirm all 5 levels render with
  sensible player counts, WAR sorting is correct within each group, and
  navigating between two different teams' depth charts (via the picker)
  shows fresh data each time (per 0061's precedent, not stale data from
  the previously-viewed team).

**Files involved:**
- `frontend/src/views/TeamDepthChart.vue` (new)
- `frontend/src/router/index.ts` (modified)
- `backend/app/api/teams.py` (modified, if a team-listing endpoint doesn't
  already exist from 0063)
