# 0040 — Defensive Optimization

- **Tag:** feat
- **Status:** Open
- **Depends on:** —
- **Blocks:** —

## 1. Problem

`docs/improvements/expanded-functionality.md`'s Tier 2 #12 asks for the best
defensive configuration for a roster — not just assigning players to their
nominal position, but comparing defensive ratings, range/arm/error-rate
history, position flexibility, and defensive WAR to find the best defensive
lineup, and to quantify the impact of moving players between positions
(best offensive lineup vs. best defensive lineup vs. best overall).

`players_fielding_position`/`players_fielding_position_talent`
(`backend/app/db/sql_scripts/schema.sql:334-...`) already carry per-position
grades, and `players_run_value.fielding_runs` exists per snapshot, but
nothing in the API or frontend surfaces a cross-position defensive comparison
or a "what if we moved X to Y" view today.

Filed as an epic-tracker ticket. Closely related to
[0039](0039-roster-optimization-org-depth.md) (Roster Optimization &
Organizational Depth) — see that ticket's Design choices for why these are
siblings rather than a strict dependency chain. Whichever of the two starts
first ends up building the shared "WAR by player by eligible position" query
layer.

## 2. Design choices

- **Outstanding — "historical defensive performance" and "error rates."**
  The source doc asks for actual (not just rated) defensive performance and
  error rates. `players_career_batting_stats`/`players_career_pitching_stats`
  exist, but there's no equivalent career **fielding** stats table (errors,
  putouts, assists, etc.) in `schema.sql` today — only rating snapshots
  (`players_fielding`, `players_fielding_position`), no box-score-style
  counting stats. Whether this ships rating-only for a v1 (skip the
  actual/historical half) or needs a new ingestion ticket first (mirroring
  [0035](0035-pitcher-career-stats-page.md)'s pattern for pitching) is
  undecided.
- **Outstanding — relationship to 0039's lineup optimizer.** If
  [0039](0039-roster-optimization-org-depth.md) builds a general lineup
  optimizer first, this ticket may reduce to "run that optimizer with a
  defense-only objective function" rather than needing its own solver. If
  this ticket lands first, it should build that piece generically enough for
  0039 to reuse rather than duplicating it. Not decided which lands first.
- **Outstanding — "position-switch scenarios."** Simulating a hypothetical
  position move (e.g. "3B → 2B") needs the target position's rating for a
  player who may not currently play there. `players_fielding_position`
  already stores grades across all 9 slots per player regardless of games
  actually played there (confirm this against a real dump — assumed from the
  wide-table shape, not yet verified the way
  [0029](0029-pitcher-pitch-repertoire.md) verified pitch-grade population),
  so this may already be answerable without new data — needs confirming.

## 3. Approach (epic outline — needs further breakdown before implementation)

- Confirm the `players_fielding_position` population assumption above
  against a real dump export before scoping further.
- Backend: extend or share the depth-chart query layer from
  [0039](0039-roster-optimization-org-depth.md) with a defense-weighted
  variant (rank by `fielding_runs`/positional grade instead of overall WAR).
- Frontend: likely a comparison view (offensive lineup vs. defensive lineup
  vs. overall lineup side-by-side), fitting the source doc's suggested
  `ROSTER › Defensive Optimization` IA placement.

**Files involved:**
- TBD once broken into sub-tickets and the 0039 relationship is resolved —
  likely shared SQL/query layer with 0039, plus a dedicated frontend
  comparison view.
