# 0039 — Roster Optimization & Organizational Depth

- **Tag:** feat
- **Status:** Open
- **Depends on:** —
- **Blocks:** —

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

- **Outstanding — no minor-league level concept exists.** `players.team_id`
  points at a `teams` row, but `teams` (`schema.sql:38-50`) has no level/
  affiliate column — no way to distinguish an org's MLB roster from its AAA/
  AA/A affiliates using data currently in `ootp`. "Organizational depth"
  (AAA/AA/A) as described in the source doc is blocked until this is
  resolved: either the OOTP dump exposes a level/affiliate field not
  currently in `DUMP_INCLUSION_LIST` (`backend/app/db/staging.py:9-16`) that
  needs ingesting, or affiliate relationships need to be inferred/ingested
  some other way. Needs inspecting a real dump export to know what's
  available.
- **Outstanding — no service-time/options data.** "Options and service-time
  considerations" from the source doc has no backing data today (no
  contract/roster-status table — same gap noted in
  [0042](0042-contract-arbitration-analyzer.md)). Likely deferred out of a v1
  scope, or dropped if the data genuinely isn't in the OOTP export.
- **Outstanding — "best lineup" optimization approach.** Computing "best
  offensive/defensive/overall lineup" is a constrained-assignment problem
  (9 roster spots, position eligibility, one player per spot). Whether this
  needs a real optimizer (e.g. a greedy per-position pass vs. a proper
  assignment-problem solve) or can get away with simple per-position "best
  projected WAR at eligible positions" sorting is not decided — depends on
  how much positional-flexibility overlap real rosters have.
- **Outstanding — platoon splits.** No handedness-vs-pitcher-handedness
  performance data is ingested (`players` has `bats`/`throws` but no split
  stats table). Likely out of scope for a first pass; the source doc's
  separate Tier 2 "Platoon & Matchup Explorer" (status: draft) already covers
  this ground and may be the more natural home for it.
- **Resolved — WAR/position data source.** `players_run_value.WAR` (batting
  side) and `players_pitching_run_value` (pitching side), joined through
  `players_rating` to the latest `rating_date` per player, plus
  `players_fielding_position`'s `pos1..pos9` grades for eligibility, are
  the existing building blocks — no new ingestion needed for the MLB-roster
  slice of this (only the org-depth/AAA-AA-A slice is blocked, per above).

## 3. Approach (epic outline — needs further breakdown before implementation)

- Resolve the minor-league-level Outstanding question first; it determines
  whether this ships as "MLB roster only" or the full org-depth scope the
  source doc describes.
- Backend: a depth-chart query layer (new module, e.g.
  `app/db/sql_scripts/api/roster_depth.sql` + a route in a new or existing
  blueprint) that joins `players` → latest `players_rating` →
  `players_run_value`/`players_pitching_run_value` →
  `players_fielding_position`, grouped by `team_id` and position.
- Lineup optimizer: once the "best lineup" Outstanding question is resolved,
  likely a small pure-Python module (parallel to
  `app/player_projection/batter.py`'s structure) rather than a SQL query,
  given the assignment-problem shape.
- Frontend: a new roster/depth-chart view (per the source doc's suggested
  `ROSTER › Roster Optimization / Organizational Depth` IA placement),
  probably a table-per-position layout.
- Feeds [0038](0038-gm-command-center.md)'s "roster weaknesses and surpluses"
  widget once it exists.

**Files involved:**
- TBD once broken into sub-tickets — likely `backend/app/db/sql_scripts/api/`
  (new SQL), a new `app/api/roster.py` blueprint, and a new frontend view
  under `frontend/src/views/`.
