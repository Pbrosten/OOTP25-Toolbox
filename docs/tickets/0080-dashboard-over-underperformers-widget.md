# 0080 — Command Center: over/underperformers widget

- **Tag:** feat
- **Status:** Open
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
  picks "latest rating" for a player.
- **Outstanding: notable-delta threshold.** What counts as "notable"
  enough to surface (e.g. actual vs. projected WAR differing by some
  fixed amount, or by a percentile band) isn't decided here — needs a
  first-pass heuristic during implementation, tunable later once real
  data shows what a reasonable threshold looks like.

## 3. Approach

New endpoint (likely `GET /api/teams/<team_id>/performance-deltas`) joining
each roster player's actual current-season WAR
(`players_career_batting_stats`/`players_career_pitching_stats`) against
their latest projected WAR
(`players_run_value`/`players_pitching_run_value`), returning a
delta-sorted list. Frontend: a widget listing top over/underperformers by
delta, scoped by `useCurrentTeam().currentTeamId`.

**Files involved:**
- `backend/app/api/teams.py` (modified) — new `performance-deltas` route.
- `backend/app/db/sql_scripts/api/` (new `.sql`).
- `frontend/src/components/dashboard/PerformanceDeltasWidget.vue` (new).
