# 0081 — Command Center: roster weaknesses/surpluses widget

- **Tag:** feat
- **Status:** Closed
- **Depends on:** —
- **Blocks:** [0085](0085-gm-command-center-dashboard.md)

## 1. Problem

[0038](0038-gm-command-center.md) calls for flagging roster
weaknesses/surpluses by position. The raw data exists —
[0063](0063-roster-depth-chart-query-api.md)'s
`GET /api/teams/<id>/depth-chart` already returns every position's
players ranked by WAR, per level — but there's no classification of which
positions actually count as "thin" or "deep." That scoring layer doesn't
exist yet.

## 2. Design choices

- **Weakness/surplus thresholds.** Resolved with the user 2026-08-23:
  league percentile, reusing the same framing already used by
  `BatterPercentiles.vue`/`PitcherPercentiles.vue` and the depth chart's
  `is_promotion_candidate` (ticket 0064) — a position group's players are
  ranked by WAR against every real MLB team's players at that same group,
  league-wide. Cutoff: 50th percentile ("league-average"). A group is a
  **weakness** if this team's best player there is below the 50th
  percentile (or the team has no rated player there at all); a
  **surplus** if 2+ of this team's players there are at/above the 50th
  percentile (multiple average-or-better options competing for one
  spot); otherwise **neutral** (a single adequate starter — not flagged
  either way, since the widget should surface what needs attention, not
  audit every position).
- **Backend vs. client-side computation.** Resolved with the user
  2026-08-23: a new backend endpoint, same pattern as 0079/0063. The
  league-wide percentile comparison needs every real MLB team's rostered
  players in the same query (not just the requested team's), which the
  existing depth-chart endpoint doesn't provide and client-side
  aggregation would mean either a second full-league fetch or duplicating
  the percentile math outside SQL.
- **Position players only.** Resolved by the user 2026-08-23: pitchers
  are excluded entirely (superseding the original SP/RP grouping below).
  A pitching-staff weakness/surplus read isn't the same shape as a
  lineup-spot one — roles are SP/RP/closer, not one starter per group
  like a batting position — so it's out of scope for this widget.
  ~~TWP excluded from grouping.~~ (moot now that all pitchers are
  excluded — a two-way player's pitching side no longer has a group to
  land in at all; their batting side is unaffected and still counts
  under their raw batting position, same as any other player.)

## 3. Approach

Added `GET /api/teams/<team_id>/roster-strength` to
`backend/app/api/teams.py`, backed by `get_team_roster_strength.sql`:
computes each real MLB position player's (pitchers excluded — `WHERE
p.position != 'P'`) league-wide percentile *and* ordinal rank
(`league_rank`, "#N of `league_pool_size`" — same framing as
`get_team_war_summary.sql`'s team power ranking, ticket 0079) within
their batting position group, returning one row per (group, this team's
player) pair — including the player's name — plus an all-NULL placeholder
row for a group with nobody rostered there. Python aggregates those rows
per group into best player/WAR/percentile/rank and the list of
at-or-above-median players (each with their own rank), classifies
weakness/surplus/neutral (`ROSTER_STRENGTH_MEDIAN_CUTOFF`/
`ROSTER_STRENGTH_SURPLUS_MIN_COUNT`), and orders groups via
`ROSTER_STRENGTH_GROUP_ORDER`. Frontend: `RosterWeaknessesWidget.vue`
lists weakness/surplus groups only (neutral groups aren't shown), naming
the actual player(s) behind each flag as a link to their player page with
their league rank (e.g. "Jordan Lawlar (#3 of 99)"), scoped by
`useCurrentTeam().currentTeamId`, wired into `LandingPage.vue`'s "Roster
Insights" section (ticket 0085).

**Files involved:**
- `backend/app/api/teams.py` (modified) — `roster-strength` route +
  classification constants.
- `backend/app/db/sql_scripts/api/get_team_roster_strength.sql` (new) —
  per-group per-player league percentile + ordinal rank query.
- `frontend/src/api/teams.ts` (modified) — `fetchTeamRosterStrength` +
  `RosterStrength`/`RosterStrengthGroup`/`RosterStrengthPlayer`/
  `RosterStrengthSurplusPlayer` types (`league_rank`/`league_pool_size`).
- `frontend/src/components/dashboard/RosterWeaknessesWidget.vue` (new).
- `frontend/src/views/LandingPage.vue` (modified) — widget wired into
  the dashboard shell's "Roster Insights" section.
