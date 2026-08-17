# 0079 — Command Center: team WAR aggregate widget

- **Tag:** feat
- **Status:** Open
- **Depends on:** —
- **Blocks:** [0085](0085-gm-command-center-dashboard.md)

## 1. Problem

[0038](0038-gm-command-center.md) (GM Command Center) calls for a headline
"team WAR" figure on the dashboard. Per-player WAR already exists
(`players_run_value`/`players_pitching_run_value`, surfaced today via
[0063](0063-roster-depth-chart-query-api.md)'s `GET /api/teams/<id>/depth-chart`),
but nothing pre-aggregates it to a single team-level total — the dashboard
would otherwise have to re-fetch and sum the full depth-chart payload just
to render one number.

## 2. Design choices

- **New endpoint vs. client-side aggregation over the depth-chart
  response.** Chosen: a small new backend endpoint. Reusing the
  depth-chart payload just to sum WAR duplicates aggregation logic on the
  frontend and couples this widget's payload size to the full roster
  response. A dedicated endpoint keeps the widget cheap to fetch and the
  summing logic in one place (SQL `SUM()`, same pattern as
  `players_career_batting_stats`'s totals).
- **MLB roster only vs. full org (incl. affiliates).** Chosen: MLB
  (`level = 1`) only for v1 — that's what "team WAR" means as a headline
  dashboard stat. Full-org/affiliate WAR is available in more detail via
  [0081](0081-dashboard-roster-weaknesses-widget.md)'s per-position
  breakdown, so isn't duplicated here.

## 3. Approach

Add `GET /api/teams/<team_id>/war-summary` to `backend/app/api/teams.py`,
summing `players_run_value.war` + `players_pitching_run_value.war` for the
team's current MLB roster (same `team_id`/`level = 1` filter as the
depth-chart route). Returns a single aggregate, e.g.
`{"team_id": ..., "war": ...}`. Frontend: a small stat-tile widget calling
this endpoint, scoped by `useCurrentTeam().currentTeamId`.

**Files involved:**
- `backend/app/api/teams.py` (modified) — new `war-summary` route.
- `backend/app/db/sql_scripts/api/` (new `.sql` if the aggregate query
  doesn't stay inline).
- `frontend/src/components/dashboard/TeamWarWidget.vue` (new).
