# 0064 — Roster depth-chart frontend view

- **Tag:** feat
- **Status:** Closed
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
- `frontend/src/views/TeamPicker.vue` (new)
- `frontend/src/router/index.ts` (modified — `/teams`, `/teams/:id/depth-chart`)
- `frontend/src/views/LandingPage.vue` (modified — entry point, matches
  the existing `tools` list pattern)
- `backend/app/api/teams.py` (modified — `GET /api/teams` listing route,
  `team_abbr` added to depth-chart player entries)
- `backend/app/db/sql_scripts/api/get_org_depth_chart.sql` (modified —
  `team_abbr`, see corrections below)
- `backend/docs/openai.yaml` (modified — document `GET /api/teams`,
  `team_abbr` field)
- `backend/tests/api/test_teams.py` (modified — new/updated tests)

**Verified** against the real `TEST.lg` save on the live dev DB
(established pattern): `GET /api/teams` returns real MLB teams;
`TeamPicker.vue` → `TeamDepthChart.vue` navigation renders all levels with
correct WAR sorting and `team_abbr` distinguishing affiliates sharing a
level. Backend suite: 126 passed. Frontend compiled cleanly via Vite HMR.

## Post-implementation correction #1: exhibition teams tagged level = 1

While building the team picker, `GET /api/teams` (with only `level = 1`
filtering) returned 4 fake "teams": AL/NL All-Stars and AL/NL Future
Stars — exhibition teams this save also tags `level = 1`, with no real
city (`city_id = 0`) and never rostering real players (`SELECT COUNT(*)
FROM players WHERE team_id IN (31,32,184,185)` → 0 for all four). See
[0062](0062-team-level-affiliate-schema-migration.md)'s addendum for the
`city_id` schema/migration addition and full investigation. **Fixed:**
`GET /api/teams` and the depth-chart route's MLB-team validity check both
now require `city_id != 0`. Added
`test_get_mlb_teams`/`test_get_team_depth_chart_exhibition_team_not_found`.

## Post-implementation correction #2: administratively-parked players

**User-reported bug:** international-complex players (age 16-18) were
showing up as MLB roster players in the depth chart.

Investigated and confirmed: `players.team_id` alone can't distinguish a
real 40-man/active MLB player from one merely administratively parked
under the parent org's `team_id` with no real minor-league assignment.
This save has no real "International Complex" team for very young
international signees to be assigned to, so OOTP parks them directly
under the parent MLB `team_id` — indistinguishable from a real roster
player via `team_id`/`level` alone. Confirmed via real data: player
138739 (age 16, "signed" to team 26) has no genuine roster slot.

The fix needed a per-player signal `players`/`teams` don't carry.
`players_roster_status` (already staged per `DUMP_INCLUSION_LIST`, but
never migrated into `ootp` — confirmed via `staging.players_roster_status`
having 16769+ rows with no destination table) has `is_active`/
`is_on_secondary` flags. Real-data investigation on team 1 (Arizona)'s
roster: 37 players with `is_active = 1` or `is_on_secondary = 1` (the real
40-man) vs. 16 with both `0` (parked prospects, matching the reported
bug). Confirmed a real AAA player (Jair Camargo, team 59, level 2) also
has `is_active = 0` — so the filter is only meaningful scoped to
`level = 1`, not applied broadly (would otherwise wrongly empty out every
real minor-league affiliate's roster).

**Chosen scope (confirmed with the user):** ingest only `is_active`/
`is_on_secondary` from `players_roster_status`'s 37 columns — the minimum
needed to fix this bug. The rest (waivers/DFA/options/service-days)
clearly matter for future tools (Trade Target Finder, Roster Optimization)
but are deliberately left uningested until a ticket actually needs them,
matching this project's established minimal-ingestion pattern (ticket
0053). Landed as two new columns on the *existing* `players_service_time`
table (already sourced from the same `staging.players_roster_status` row
for `mlb_service_years`/etc.), not a new table — see
[0053](0053-contract-service-time-schema.md)'s addendum.

**Fixed:**
- `backend/app/db/sql_scripts/schema.sql`: added `is_active`/
  `is_on_secondary BOOLEAN` to `players_service_time`. (Also fixed, while
  here: two pre-existing/newly-introduced instances of ticket 0055's
  semicolon-inside-a-SQL-comment bug — a linter pass had converted
  mid-sentence `--` dashes into `;` in this file, breaking
  `init_database()`'s naive `.split(";")` statement splitter. One was in
  this ticket's own new `teams`/`players_service_time` comments, one was
  pre-existing in the unrelated `players_pitch_repertoire` comment. Fixed
  by rewording both to avoid semicolons inside comments entirely, per
  0055's established pattern — verified via a script that runs
  `init_database()`'s exact split-and-execute logic against the file.)
- `backend/app/db/sql_scripts/migration/migration_long.sql`: added
  `is_active`/`is_on_secondary` to the existing `players_service_time`
  INSERT (both the column list and `ON DUPLICATE KEY UPDATE`).
- `backend/app/db/sql_scripts/api/get_org_depth_chart.sql`: the `roster`
  CTE now `LEFT JOIN`s `players_service_time` and filters
  `WHERE ot.level != 1 OR st.is_active = 1 OR st.is_on_secondary = 1`.

**Re-verified** end-to-end against the live dev DB (schema/migration
changes first verified on a throwaway DB, then applied to the persistent
dev-stack `ootp` database via `flask init-db` + `flask update-db`, per
user request): player 138739 (the reported case) no longer appears in
team 26's depth chart; a real active MLB player (Corbin Carroll, 23790)
still appears; team 1's MLB-level count dropped from 54 to the correct 37;
team 1's AAA/AA/A/Rookie counts (16/20/55/104) are completely unchanged,
confirming the filter didn't touch real minor-league rosters. Backend
suite: 126 passed (no new tests added for this SQL-only filter — no
existing precedent in this codebase for SQL-level automated tests;
verification is documented here instead, matching how 0062/0063's
schema/migration changes were verified).

**Files involved (addendum):**
- `backend/app/db/sql_scripts/schema.sql` (modified again — `is_active`/
  `is_on_secondary`, plus the semicolon-in-comment fixes)
- `backend/app/db/sql_scripts/migration/migration_long.sql` (modified
  again — `is_active`/`is_on_secondary`)
- `backend/app/db/sql_scripts/api/get_org_depth_chart.sql` (modified
  again — the `is_active`/`is_on_secondary` filter)

## Post-implementation correction #3: visual redesign per user feedback

**User-reported:** stacking all 5 levels vertically (MLB → AAA → AA → A →
Rookie, each with its own grid of position cards) caused excessive
scrolling, and the plain-bordered cards looked rough.

**Fixed:** `TeamDepthChart.vue` rewritten to use Headless UI's
`TabGroup`/`Tab`/`TabPanel` (already a project dependency —
`BatterPercentiles.vue`/`PitcherPercentiles.vue` already use `Listbox`
from the same library for year selection, so this matches an existing
convention rather than introducing a new one) — one tab per level, only
the selected level's position cards render at a time. Card styling
tightened to match the rest of the app's established look (`SurplusValue.
vue`'s `rounded`/`bg-gray-50`/teal-accent conventions): `rounded-lg
shadow-sm border` cards, a teal uppercase group header with a bottom
rule, and WAR values colored teal (non-negative) or red (negative,
mirroring `SurplusValue.vue`'s surplus-sign convention) instead of plain
black text.

**Verified:** Vite HMR recompiled cleanly, no runtime errors. `npx
vue-tsc -b` reports 2 new "Cannot find module" errors for the two new
view files (`TeamDepthChart.vue`, `TeamPicker.vue`) — the same
pre-existing module-resolution noise every other view/component already
produces in this environment (confirmed by diffing against the categories
already present in the 32-error baseline), not a real type issue. Live
page load at `/teams/3/depth-chart` returns 200 with all 5 real levels
present.

**Files involved (addendum):**
- `frontend/src/views/TeamDepthChart.vue` (rewritten — tabs + card styling)

## Post-implementation correction #4: WAR is misleading below MLB, promotion indicator, org theming

**User-reported problem:** projected WAR is computed from *current*
ratings evaluated as if the player were already in MLB (confirmed by
reading `batter.py`/`pitcher.py`: hardcoded MLB-relative constants —
`LG_WOBA = 0.325`, `RUNS_WIN = 9.92`, `RA9_BASELINE = 4.65`, etc. — with
no level/league adjustment anywhere in the pipeline). For a prospect who
hasn't developed yet, this systematically understates their real future
value, and ranking non-MLB levels by it answers "who's best right now
relative to MLB" rather than "who's the most promising prospect," which
matters more long-term. Separately checked whether a real
Potential/Future-Value field could replace it: the raw dump has no single
FV scalar, only per-attribute talent grades (`batting_ratings_talent_*`
etc., already ingested into `players_batting_talent`/`players_pitching_
talent`/`players_fielding_position_talent` via `migration_short.sql`, but
never used for projections) — building a real talent-based WAR would mean
a whole parallel projection methodology (same scope as ticket 0026), not
a quick fix.

**Resolved (confirmed with the user) — three changes:**

1. **A/Rookie levels (4, 6) show roster counts per position only, no
   player list or WAR.** AAA/AA (2, 3) keep full WAR-ranked lists — close
   enough to MLB-readiness that current-rating WAR remains a reasonable
   signal there, per the user's own "below AA" framing. MLB (1) is
   unaffected.
2. **Promotion-candidate indicator, AAA/AA only.** Per the user's
   explicit rule: flag a player whose WAR is in the top 20% of every
   player at that *same level, league-wide* (all orgs, not just the one
   being viewed) — not a per-org/per-position relative comparison (an
   earlier per-group-margin idea was dropped after checking real data:
   AAA/AA position groups are tiny, 1-6 players, with WAR gaps too small
   and noisy to threshold reliably; a league-wide percentile avoids that
   entirely). Verified the SQL's own calculation against an independent
   Python percentile computation over all 546 real AAA players — matched
   exactly (both flagged players landed at the ~88th percentile against
   the 80th-percentile cutoff of 0.778 WAR).
3. **Org color theming**, scoped to this page only (not app-wide — see
   [0065](0065-gm-org-selection-theming.md), filed separately per the
   user's explicit request not to build the app-wide "GM tab"/org-
   selection version now). Uses the MLB team's real
   `teams.background_color`/`text_color` (already ingested, unused until
   now), applied via CSS custom properties to the page header and active
   tab.

**Implementation:**
- `backend/app/db/sql_scripts/api/get_org_depth_chart.sql`: added a
  `league_level_war` CTE (every player at level 2 or 3 across the whole
  league, not scoped to `org_teams`) and an `is_promotion_candidate`
  column computed the same way this codebase's other percentile queries
  already are (`COUNT(lower) / COUNT(total) >= 0.8`, matching
  `get_player_expected_value_percentiles.sql`'s established pattern)
  rather than a window function, for stylistic consistency.
- `backend/app/api/teams.py`: added `COUNT_ONLY_LEVELS = {4, 6}` —
  the grouping loop now produces a plain integer count for those levels
  instead of a player-entry list; `is_promotion_candidate` passed through
  for the WAR-ranked levels. `team_name`/`background_color`/`text_color`
  added to the top-level response (queried alongside the existing
  `level`/`city_id` validity check, no new query).
- `frontend/src/views/TeamDepthChart.vue`: `COUNT_ONLY_LEVELS` renders a
  compact count-tile grid instead of position cards; an
  `ArrowUpCircleIcon` (Heroicons, already a dependency) renders next to a
  promotion candidate's name; `teamColors` computed property sets
  `--team-bg`/`--team-text` CSS custom properties from the API response,
  applied to the header banner and the active tab.

**Bug found and fixed during verification:** `is_promotion_candidate`'s
SQL comment originally read "top 20% of every player" — pymysql's
parameter substitution runs Python's `%`-style string formatting over the
*entire* query text (not just placeholders), and `"% o"` (percent, space,
then a letter) parses as a valid flag+conversion format spec, raising
`TypeError: %o format: an integer is required, not dict` at request time.
Fixed by rewording the comment to avoid a bare `%` character entirely
("top fifth (80th percentile or higher)" instead of "top 20%"). Swept the
rest of `backend/app/db/sql_scripts/api/*.sql` for the same hazard
(`grep -no '%[^(]'`) — the only other bare `%` occurrences are
pre-existing, legitimate positional `%s` placeholders in unrelated files,
not a bug.

**Re-verified** against the live dev DB: `GET /api/teams/1/depth-chart`
returns `team_name`/`background_color`/`text_color`; levels 4/6 return
plain `{position: count}` objects (spot-checked: level 4 `SS: 4`, level 6
`C: 11`); level 2's `SP` group shows two players flagged
`is_promotion_candidate: true` (Fuerte 1.06 WAR, Perez 1.05 WAR), matching
the independent percentile check above; level 1 never flags anyone.
Backend suite: 129 passed (11 in `test_teams.py`, including 3 new tests
for count-only levels, the promotion flag, and team metadata). Frontend
compiled cleanly via Vite HMR; `npx vue-tsc -b` unchanged from the prior
34-error baseline (no new real errors). Live page load at
`/teams/1/depth-chart` returns 200.

**Files involved (addendum):**
- `backend/app/db/sql_scripts/api/get_org_depth_chart.sql` (modified
  again — `league_level_war` CTE, `is_promotion_candidate`, `%` fix)
- `backend/app/api/teams.py` (modified again — `COUNT_ONLY_LEVELS`,
  `is_promotion_candidate` passthrough, `team_name`/color fields)
- `backend/docs/openai.yaml` (modified again)
- `backend/tests/api/test_teams.py` (modified again — 3 new tests)
- `frontend/src/views/TeamDepthChart.vue` (modified again — count tiles,
  promotion icon, org color theming)

## Post-implementation correction #5: two-column position/pitcher layout

**User-requested:** for MLB/AAA/AA, split into two columns — position
players (C/1B/2B/3B/SS/LF/CF/RF, plus DH per this app's existing DH-as-
batter convention, see [0060](0060-exclude-dh-from-fielding-percentiles.md))
on the left, pitchers (SP/RP) on the right, rather than one flat grid of
position cards.

**Fixed:** `TeamDepthChart.vue`'s WAR-ranked-levels branch now renders a
`grid-cols-1 lg:grid-cols-2` outer layout, iterating over two columns
(`{ label: 'Position Players', groups: batterGroups(...) }`,
`{ label: 'Pitchers', groups: pitcherGroups(...) }`) built from two new
helpers that filter `sortedGroups`'s existing output by whether the group
is in `PITCHER_GROUPS = {'SP', 'RP'}`. The per-position card markup itself
is unchanged, just nested one level deeper. Count-only levels (4, 6) are
unaffected — still a single flat tile grid, since the two-column split
was only requested for the WAR-ranked levels.

**Verified:** Vite HMR recompiled cleanly, live page load at
`/teams/1/depth-chart` returns 200, `npx vue-tsc -b` unchanged from the
34-error baseline (no new real errors).

**Files involved (addendum):**
- `frontend/src/views/TeamDepthChart.vue` (modified again — two-column
  position/pitcher layout)

## Post-implementation correction #6: player names link to their player page

**User-requested:** clicking a player name in the depth chart should
navigate to that player's page.

**Fixed:** wrapped each player name in a `<router-link :to="\`/players/
${player.player_id}\`">` (the existing `/players/:id` route,
`PlayerProfile.vue`), with a hover underline/color matching this app's
other in-app link conventions. Only applies to levels 1/2/3 (the
WAR-ranked levels that show individual player names at all) — levels 4/6
show counts only, per this ticket's earlier correction, so there's
nothing to link there. Navigating in and back out is already covered by
[0061](0061-refetch-player-data-on-route-param-change.md)'s
`<router-view :key>` fix, so no stale-data risk on return.

**Verified:** Vite HMR recompiled cleanly, live page load at
`/teams/1/depth-chart` returns 200, `npx vue-tsc -b` unchanged from the
34-error baseline.

**Files involved (addendum):**
- `frontend/src/views/TeamDepthChart.vue` (modified again — player-name
  router-links)

## Known issue #7: 500 error for orgs rostering a two-way player (not yet fixed — see 0067)

**User-reported:** 11 orgs' depth charts (Red Sox, Reds, Rockies, Astros,
Royals, Angels, Mets, Giants, Rays, Rangers, Nationals) fail to load with
a 500 Internal Server Error.

**Root cause, confirmed against live data and the raw dump export:**
`GET /api/teams/<id>/depth-chart` crashes in `jsonify()` with
`TypeError: '<' not supported between instances of 'NoneType' and 'str'`.
14 players league-wide (one or two per each of the 11 reported orgs —
every affected player's org root, via `parent_team_id` for affiliates,
matches exactly one of the 11 reported teams) have `position = 'P'` but
no `players_pitching` row at their latest rating snapshot. In
`get_org_depth_chart.sql`, `role_group` (`CASE pp.role WHEN 11 THEN
'SP' ...`) resolves to `NULL` via the `LEFT JOIN`. In
`app/api/teams.py`'s grouping loop, that becomes a Python `None` used as
a dict key (`levels[level][None] = ...`) alongside ordinary string keys
(`'SP'`, `'1B'`, etc.). Flask's `jsonify()` sorts dict keys by default,
and comparing `None < 'SS'` raises the `TypeError` above — crashing the
whole response for any org that happens to roster one of these players.
This bug has existed since [0063](0063-roster-depth-chart-query-api.md)
shipped; it simply hadn't been triggered by Arizona, the org used
throughout 0063/0064's own verification.

**Investigated further, per the user's request:** all 14 players are
genuine two-way players (confirmed via `players_career_batting_stats`/
`players_career_pitching_stats` both showing real, substantial 2029
usage — e.g. Bryce Eldridge: 143 G/569 PA batting, 5 G/8 IP pitching).
Traced precisely: the raw dump's `players_pitching.mysql.sql` **does**
include a row for these players every heap, but OOTP's own per-heap
`role` field toggles between a real pitcher role (11/12/13) and `0`
(non-pitcher) depending on which side of their game was recently
emphasized — confirmed directly against Eldridge's December 2029 row:
`role = 0`. `migration_short.sql`'s `players_pitching` INSERT filters
`WHERE s.role IN (11, 12, 13)` (from
[0026](0026-pitcher-projection-methodology.md)), so a heap where a TWP's
role reads `0` silently drops their pitching ratings entirely for that
month — not an OOTP export gap, our own ingestion filter not
anticipating a toggling role value.

**Not fixed here.** This is exactly the two-way-player gap
[0030](0030-exclude-pitchers-from-batting-projection.md) explicitly
deferred ("a future TWP tag... belongs entirely to that future ticket")
— filed as [0067](0067-two-way-player-detection.md), which also captures
new evidence that changes 0030's original assumption about how TWP
detection would need to work (the `role` field itself already signals
it, no threshold-derivation needed). 0067 needs its own design-question
round before implementation (detection rule, ingestion-filter shape,
`role_group` fallback, and whether the existing "never net batting/
pitching WAR" exclusion elsewhere in the app still holds once TWP data
is reliable) — not resolved here. The 11 orgs' depth charts remain
broken until 0067 (or a narrower stopgap) ships.

**Files involved:** none yet — diagnosis only, fix deferred to
[0067](0067-two-way-player-detection.md).
