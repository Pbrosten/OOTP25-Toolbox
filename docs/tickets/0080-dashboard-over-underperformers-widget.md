# 0080 — Command Center: over/underperformers widget

- **Tag:** feat
- **Status:** Closed
- **Depends on:** —
- **Blocks:** [0085](0085-gm-command-center-dashboard.md)

## 1. Problem

[0038](0038-gm-command-center.md) calls for surfacing players who are
over/underperforming their projections. This was originally listed as
blocked in 0038's Design choices, but that was written before real-game
actual WAR was ingested: `players_career_batting_stats.war` and
`players_career_pitching_stats.war` (by player/year/team_id) exist now,
alongside the already-existing projected WAR
(`players_run_value`/`players_pitching_run_value`). No endpoint currently
diffs the two — this is an integration gap, not a data gap.

## 2. Design choices

- **Which season's actual stats to compare against which projection
  snapshot.** `players_career_batting_stats`/`_pitching_stats` are keyed
  by year; projections come from the latest ratings heap. Chosen: compare
  the current season's actual-WAR-to-date against the most recent
  projection snapshot for the same player — mirrors how
  [0056](0056-surplus-value-calculation.md)'s surplus-value calc already
  picks "latest rating" for a player. Resolved at implementation time:
  "current season" is the single most recent year recorded *across the
  whole save* (`GREATEST` of both career tables' own `MAX(year)`), not
  each player's own last-recorded year — a real bug caught while
  building the query: a player who debuted in an earlier season and
  hasn't played yet this one was defaulting to `actual_war = 0`, which
  read as "underperforming" a positive projection when he simply hasn't
  played. Such a player is now excluded outright (no qualifying row for
  the current year at all), not zero-filled.
- **Notable-delta threshold.** Resolved at implementation time (data
  investigated on a real team's roster, `1.0` WAR chosen as a first pass
  — see `PERFORMANCE_DELTA_NOTABLE_THRESHOLD`'s comment in
  `app/api/teams.py` for the exact reasoning/observed range): a delta
  matters if it's worth a real, standalone win of value, not just noise.
- **Minimum-sample floor, not originally flagged as a design question but
  found necessary during implementation.** A tiny sample (e.g. an 8-PA
  September call-up) can produce a huge, meaningless delta purely from
  small-sample noise. Fixed by reusing this codebase's own existing
  "qualifying sample" convention from ticket 0066's league-baseline calc
  (`get_batting_league_baseline_pool.sql`/
  `get_pitching_league_baseline_pool.sql`): PA >= 50 for batters, outs >=
  60 (~20 IP) for pitchers — same thresholds, same rationale, reused
  rather than inventing a new cutoff.

## 3. Approach

Added `GET /api/teams/<team_id>/performance-deltas` to
`backend/app/api/teams.py`, backed by `get_team_performance_deltas.sql`:
for the team's active MLB roster, joins each player's actual current-
season WAR (batting + pitching summed for a two-way player, same
convention as `get_team_war_summary.sql`) against their latest projected
WAR, filtered to a qualifying real-stat sample and the single
save-wide current year (see Design choices). Python filters to
`|delta| >= PERFORMANCE_DELTA_NOTABLE_THRESHOLD` and returns them
already delta-descending (the SQL's own order, preserved through the
filter). Frontend: `PerformanceDeltasWidget.vue` splits that list into
Overperforming/Underperforming columns, same two-column layout as
`RosterWeaknessesWidget.vue` (ticket 0081), scoped by
`useCurrentTeam().currentTeamId`, wired into `LandingPage.vue`'s
"Roster Insights" section (ticket 0085) alongside 0081/0082's widgets.

**Files involved:**
- `backend/app/api/teams.py` (modified) — `performance-deltas` route +
  `PERFORMANCE_DELTA_NOTABLE_THRESHOLD`.
- `backend/app/db/sql_scripts/api/get_team_performance_deltas.sql` (new)
  — actual-vs-projected WAR query.
- `frontend/src/api/teams.ts` (modified) — `fetchTeamPerformanceDeltas` +
  `PerformanceDeltas`/`PerformanceDeltaPlayer` types.
- `frontend/src/components/dashboard/PerformanceDeltasWidget.vue` (new).
- `frontend/src/views/LandingPage.vue` (modified) — widget wired into
  the dashboard shell's "Roster Insights" section.
