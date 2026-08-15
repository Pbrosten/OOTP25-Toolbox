# 0039 — Roster Optimization & Organizational Depth

- **Tag:** feat
- **Status:** In-Progress
- **Depends on:** [0062](0062-team-level-affiliate-schema-migration.md)
- **Blocks:** [0063](0063-roster-depth-chart-query-api.md), [0064](0064-roster-depth-chart-frontend.md)

## 1. Problem

`docs/improvements/expanded-functionality.md`'s Tier 1 #2 asks "who should
actually be on the roster, and where does everyone fit?" — MLB roster
analysis, AAA/AA/A organizational depth, projected WAR by player and
position, position eligibility/defensive versatility, platoon splits,
options/service-time, prospect readiness, best-lineup combinations, a
position-by-position depth chart, and org-wide surplus/weakness detection.

Nothing in the app currently answers this. `players_run_value`/
`players_pitching_run_value` already carry per-snapshot WAR
(`backend/app/db/sql_scripts/schema.sql:379-387`), and
`players_fielding_position` carries per-position ratings, but nothing
aggregates them into "who's the best 1B on this org's depth chart" or "what's
our best projected lineup" — there's no roster/depth-chart concept in the API
(`backend/app/api/players.py`, `ratings.py`) or frontend at all.

Filed as an epic-tracker ticket in the style of [0015](0015-pitcher-projection-epic.md);
needs breakdown into per-subsystem tickets once prioritized. Closely related
to [0040](0040-defensive-optimization.md) (Defensive Optimization) — that
ticket's "best defensive lineup"/"position-switch scenarios" output overlaps
with this one's "best defensive roster"/"position-by-position depth chart."
They're filed as siblings under the same epic rather than one blocking the
other, since either could plausibly be scoped first; whichever lands first
should expect to build the shared "WAR by player by position" query the other
will also need.

## 2. Design choices

- **Resolved — minor-league level concept.** Inspected a real dump export
  (`TEST.lg` save) and found `teams.mysql.sql` already carries
  `parent_team_id` and `level` columns in the raw OOTP export — level 1 =
  MLB, 2 = AAA, 3 = AA, 4 = A/High-A, 6 = Rookie/Complex (level 5 turned
  out to be 2 "All-Star" exhibition teams specific to this save, not a
  real tier, and needs excluding). Filed as the prerequisite
  [0062](0062-team-level-affiliate-schema-migration.md), mirroring the
  0053/0054 pattern from the Contract Analyzer epic — chosen over shipping
  an MLB-only v1 first, since the data turned out to already be one small
  schema+migration change away rather than a real gap.
- **Resolved — service-time/options data.** No longer a gap —
  [0042](0042-contract-arbitration-analyzer.md) (Contract & Arbitration
  Analyzer) closed since this ticket was filed, so `players_contract`/
  `players_service_time` now exist. **Chosen (confirmed with the user):**
  still keep this first pass focused on WAR/position-eligibility only —
  service-time/options-aware roster decisions are a real future layer, not
  dropped, but sequenced after the core depth chart exists to build on.
- **Resolved — "best lineup" optimization approach.** **Chosen (confirmed
  with the user):** defer entirely — ship a position-by-position depth
  chart (ranked by projected WAR) as v1, which is useful on its own and
  much simpler than the constrained-assignment "best 9" problem. The
  optimizer itself (greedy vs. a proper assignment-problem solve) isn't
  ticketed yet; revisit once the depth chart ships and real usage shows
  how much positional-flexibility overlap matters in practice.
- **Resolved — platoon splits.** **Chosen (confirmed with the user):** out
  of scope for this epic. No handedness-vs-pitcher-handedness data is
  ingested; the source doc's separate Tier 2 "Platoon & Matchup Explorer"
  is the more natural home for this if it's ever built.
- **Resolved — WAR/position data source.** `players_run_value.WAR`
  (batting side) and `players_pitching_run_value` (pitching side), joined
  through `players_rating` to the latest `rating_date` per player, plus
  `players_fielding_position`'s `pos1..pos9` grades (mapped to C/1B/2B/
  3B/SS/LF/CF/RF per `batter.py`'s existing convention) for eligibility,
  are the existing building blocks — no new ingestion needed beyond
  0062's level/affiliate columns.

## 3. Approach (epic outline — broken down into sub-tickets below)

- Team level/affiliate ingestion: [0062](0062-team-level-affiliate-schema-migration.md) —
  adds `parent_team_id`/`level` to `teams`, unblocking the full org-depth
  scope (not just MLB-only) from the start.
- Depth-chart query layer + API route:
  [0063](0063-roster-depth-chart-query-api.md) — joins `players` → latest
  `players_rating` → `players_run_value`/`players_pitching_run_value` →
  `players_pitching` (for SP/RP role), grouped by org/level/position, a
  new `app/api/teams.py` blueprint.
- Frontend: [0064](0064-roster-depth-chart-frontend.md) — a new
  `TeamDepthChart.vue` view (per the source doc's suggested
  `ROSTER › Roster Optimization / Organizational Depth` IA placement), one
  table per level/position group.
- Lineup optimizer (best 9-man lineup): deliberately not ticketed yet —
  see Design choices above. File once the depth chart ships and real
  usage shows whether a greedy or proper assignment-problem solve is
  actually needed.
- Feeds [0038](0038-gm-command-center.md)'s "roster weaknesses and surpluses"
  widget once it exists.

**Files involved:**
- Team level/affiliate ingestion: see
  [0062](0062-team-level-affiliate-schema-migration.md) for exact files.
- Depth-chart query + API: see
  [0063](0063-roster-depth-chart-query-api.md) for exact files.
- Frontend: see [0064](0064-roster-depth-chart-frontend.md) for exact
  files.
