# 0063 — Roster depth-chart query layer + API route

- **Tag:** feat
- **Status:** Open
- **Depends on:** [0062](0062-team-level-affiliate-schema-migration.md)
- **Blocks:** [0064](0064-roster-depth-chart-frontend.md)

## 1. Problem

[0039](0039-roster-optimization-org-depth.md)'s core ask: given an MLB
team, show its full organizational depth chart — its MLB roster plus its
AAA/AA/A/Rookie affiliates (per [0062](0062-team-level-affiliate-schema-migration.md)'s
`parent_team_id`/`level` data), players ranked by projected WAR at their
position, so a GM can see organizational strengths and weaknesses
position-by-position.

Per the epic's confirmed scope: this is a depth chart only for v1, not a
lineup optimizer ([0039](0039-roster-optimization-org-depth.md)'s "best
9-man lineup" question is explicitly deferred to a future ticket), and
stays focused on WAR/position-eligibility — no service-time/options
weighting, no platoon splits.

## 2. Design choices

- **Org scope: the given MLB team plus every team whose
  `parent_team_id` equals it.** Confirmed in
  [0062](0062-team-level-affiliate-schema-migration.md)'s investigation
  that every MiLB affiliate's `parent_team_id` points directly at its MLB
  parent (no chain to walk), and that `level = 5` (2 "All-Star" exhibition
  teams in the `TEST.lg` save) and `team_id = 999` (Free Agents) aren't
  real affiliates and must be excluded from the org tree, the same way
  `team_id != 999` already gates other roster-scoped queries (e.g.
  `get_player_expected_value_percentiles.sql`).
- **Depth-chart grouping: by each player's own primary `position`, not a
  cross-position eligibility grade.** Options considered — (a) group each
  player under their own `players.position` (their primary/roster
  position) at each level, ranked by WAR within that group; (b) also
  surface cross-position eligibility, e.g. list a shortstop under 2B/3B
  too if his `players_fielding_position` grade there clears some
  threshold, to reflect "defensive versatility" from the source doc.
  **Chosen: (a).** Matches the agreed v1 scope (depth chart, not the
  full lineup-optimizer/versatility pass) and needs no new eligibility-
  threshold design question — every position player already has exactly
  one `position` value to group by, the same field
  [0060](0060-exclude-dh-from-fielding-percentiles.md) and
  `BatterPercentiles.vue` already key off of. (b) is real scope from the
  source doc but adds a genuinely new question (what fielding-grade
  threshold counts as "eligible" at a position — nothing in the codebase
  answers this today) that's cleaner to resolve later as its own
  versatility-focused sub-ticket once the primary-position depth chart
  ships and it's clear whether it's actually needed.
- **Pitchers grouped by role (SP/RP), not lumped as one "P" bucket.**
  `players_pitching.role` (11/12/13, mapped to SP/RP per
  [0037](0037-split-sp-rp-percentile-cohorts.md)'s established
  `ROLE_MAP`) is already ingested and already used this way elsewhere in
  the codebase — reusing it here avoids a depth chart where a team's top
  5 starters and top 8 relievers are all interleaved into one
  undifferentiated "Pitching" group ranked by WAR, which would be much
  less useful than seeing SP and RP depth separately.
- **WAR source: `players_run_value`/`players_pitching_run_value`, latest
  rating per player — same source [0039](0039-roster-optimization-org-depth.md)'s
  Design choices already resolved.** No new WAR computation, just a new
  query shape (grouped by org/level/position instead of by single player).
- **Outstanding:** none new — the remaining real open question (cross-
  position versatility) is deliberately deferred above, not left
  undecided within this ticket's own scope.

## 3. Approach

- New SQL, `backend/app/db/sql_scripts/api/get_org_depth_chart.sql`:
  - `org_teams` CTE: the given `team_id` plus every team where
    `parent_team_id = team_id`, excluding `level = 5` (hardcoded, per
    0062's finding that it's not a real minor-league tier in this save)
    and `team_id = 999`.
  - Join `players` → latest `players_rating` per player → LEFT JOIN
    `players_run_value`/`players_pitching_run_value` for WAR → LEFT JOIN
    `players_pitching` for role (SP/RP bucket, `NULL` for position
    players) → filter to `player.team_id IN (org_teams)`.
  - Return one row per player: `player_id`, `first_name`, `last_name`,
    `team_id`, `level`, `position`, `role_group` (SP/RP/`NULL`), `war`
    (batting or pitching WAR, whichever applies — same "two-way players
    get neither" precedent as
    [0056](0056-surplus-value-calculation.md) if both are present, since
    there's no established way to net them yet either).
  - Grouping/ranking by level+position+role_group happens in the API
    layer (Python), not SQL — mirrors how `get_player_contract_inputs.sql`
    stays a flat row-returning query and `contract_value.py` does the
    shaping, rather than a deeply nested SQL aggregation.
- New blueprint, `backend/app/api/teams.py`, registered in
  `app/__init__.py` alongside the existing four blueprints:
  - `GET /api/teams/<int:team_id>/depth-chart`: runs the query above,
    groups rows into `{level: {position_or_role_group: [players sorted by
    WAR desc]}}`, returns as JSON. 404 if `team_id` isn't a real MLB team
    (`level != 1`) — a depth chart is always requested by its MLB root,
    not by an individual affiliate's `team_id`.
- Verify against the real `TEST.lg` save on the live dev DB (established
  pattern, once 0062 has ingested `level`/`parent_team_id`): confirm a
  real org's depth chart returns all 5 levels (MLB/AAA/AA/A/Rookie) with
  the affiliate counts matching 0062's investigation for that org, that
  SP/RP are correctly split, that a spot-checked player's WAR matches
  what their individual `/api/players/<id>/...` percentile routes report,
  and that requesting a non-MLB `team_id` 404s.

**Files involved:**
- `backend/app/db/sql_scripts/api/get_org_depth_chart.sql` (new)
- `backend/app/api/teams.py` (new)
- `backend/app/__init__.py` (modified — register the new blueprint)
- `backend/docs/openai.yaml` (modified — document the new route, per
  CLAUDE.md)
