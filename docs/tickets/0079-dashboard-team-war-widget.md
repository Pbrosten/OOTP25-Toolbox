# 0079 — Command Center: team power ranking widget

- **Tag:** feat
- **Status:** Closed
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

**Revised by the user 2026-08-23**: a raw WAR number means little without
league context, so the headline stat is a power ranking — this team's
rank among all 30 real MLB teams by that same roster-WAR aggregate — with
the raw WAR figure kept as supporting detail underneath.

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
- **`RANK()` vs. `ROW_NUMBER()` for the ranking.** Chosen: `RANK()` —
  teams tied on WAR share the same rank (with a gap afterward, e.g. two
  teams tied at 5th, next team is 7th), the standard "power ranking"
  convention, rather than an arbitrary tiebreak ordering two equal teams
  1st/2nd.
- **Ranking scope: all real MLB teams, computed in one query.** The
  query builds every real MLB team's WAR total first (`mlb_teams`/
  `team_war` CTEs in `get_team_war_summary.sql`), including teams with no
  rated roster players yet (WAR = 0 via `LEFT JOIN`, not simply absent
  from the ranking) — ranking only among teams that happened to already
  have a matching row would silently drop winless/unrated teams from the
  denominator instead of correctly ranking them last.

## 3. Approach

Added `GET /api/teams/<team_id>/war-summary` to `backend/app/api/teams.py`,
backed by `get_team_war_summary.sql`: sums `players_run_value.WAR` +
`players_pitching_run_value.WAR` per real MLB team's current active
roster, then ranks all 30 with `RANK() OVER (ORDER BY war DESC)`. Returns
`{"team_id": ..., "war": ..., "rank": ..., "total_teams": ...}` for the
requested team. Frontend: `TeamWarWidget.vue` leads with `#{rank} of
{total_teams}`, WAR shown as detail underneath — scoped by
`useCurrentTeam().currentTeamId`.

**Files involved:**
- `backend/app/api/teams.py` (modified) — `war-summary` route.
- `backend/app/db/sql_scripts/api/get_team_war_summary.sql` (new) —
  aggregate + power-ranking query.
- `frontend/src/api/teams.ts` (modified) — `fetchTeamWarSummary` +
  `TeamWarSummary` type (`war`/`rank`/`total_teams`).
- `frontend/src/components/dashboard/TeamWarWidget.vue` (new).
