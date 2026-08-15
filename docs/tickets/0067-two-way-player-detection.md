# 0067 — Two-way player (TWP) detection and dual-sided pitching ingestion

- **Tag:** feat
- **Status:** Closed
- **Depends on:** —
- **Blocks:** —

## 1. Problem

The 500 error in [0064](0064-roster-depth-chart-frontend.md)'s org depth
chart (11 orgs, 14 players) traced back to genuine two-way players — real
usage confirmed via `players_career_batting_stats`/`players_career_
pitching_stats` (e.g. Bryce Eldridge: 143 G / 569 PA batting **and** 5 G /
8 IP pitching in 2029). This is exactly the gap
[ticket 0030](0030-exclude-pitchers-from-batting-projection.md) deferred:
*"players with average-or-above skill/potential in both hitting and
pitching should be tagged (e.g. `TWP`) and continue receiving both
batting and pitching projections... unresolved and belongs entirely to
that future ticket."* This is that ticket.

**New evidence changes 0030's original assumption.** 0030 believed there
was "no native hook to lean on" and a TWP tag "would have to be *derived*
from rating thresholds." Investigating the 0064 crash found something
more direct: **OOTP's own per-heap `role` field already toggles between
pitcher (11/12/13) and non-pitcher (0) for a TWP, month to month,
tracking which side of their game is currently emphasized** — not a
fixed designation. Confirmed directly against the raw `TEST.lg` export
(`dump_2029_12/mysql/players_pitching.mysql.sql`): Eldridge's December
row is `(43866, 25, 203, position=9, role=0, ...)` — the raw dump
**does** include a pitching-ratings row for him that month, tagged
`role = 0` (non-pitcher), because his recent usage leaned batting that
month.

`migration_short.sql`'s `players_pitching` INSERT (from
[0026](0026-pitcher-projection-methodology.md)) filters
`WHERE s.role IN (11, 12, 13)` — a deliberate, correctly-reasoned filter
at the time (excluding non-pitchers from a table meant only for
pitchers), but it doesn't anticipate a player whose `role` value
legitimately flips back and forth. **Net effect:** whenever a TWP's role
reads `0` in a given heap, this app silently has no `players_pitching`
row for them that month — no pitching rating, no pitching WAR/value, and
(the immediate trigger) a `NULL` `role_group` wherever code assumes every
`position = 'P'` player resolves to `SP`/`RP`
(`get_org_depth_chart.sql`), which crashed the depth chart via a `None`
dict key hitting Flask's default key-sorting JSON serialization. Their
batting side is mostly unaffected — `players_batting`'s parallel filter
(`role NOT IN (11, 12, 13)`) already keeps their batting ratings flowing
in months where their batting-file role isn't a pitcher role, which
appears to be the common case for them, so `players_run_value`/batting
WAR already exists for these players today. It's specifically the
**pitching side that intermittently disappears**.

## 2. Design choices

- **Detection: reuse already-ingested career stats, not rating
  thresholds.** 0030 assumed detection would need inferring "average or
  above" from `players_batting_talent`/`players_pitching_talent` grades
  — genuinely ambiguous (what counts as "average," which fields). The
  investigation above found a much more direct, already-available signal:
  a player has recent-year rows in **both**
  `players_career_batting_stats` and `players_career_pitching_stats`
  (real, in-game usage on both sides) — no threshold judgment call
  needed, no new ingestion. **Chosen (confirmed with the user):** any
  `PA > 0` and any `IP > 0` in the current heap's year, no minimum-volume
  floor — simplest, no arbitrary cutoff to justify; the cost of a false
  positive (a pure pitcher's token pinch-hit appearance) is just one
  extra ingested rating row for that player that month, not a real
  problem.
- **Ingestion fix: stop dropping a detected TWP's ratings on either side
  when `role` doesn't match that side's usual filter.** For a detected
  TWP, `players_batting`/`players_batting_talent` are now ingested even
  when `role IN (11,12,13)` (previously excluded, symmetric risk found
  during implementation — a TWP's role reading as a pitcher role in a
  given heap was silently dropping their *batting* ratings that month,
  the mirror image of the reported bug), and `players_pitching`/
  `players_pitching_talent` are ingested even when `role = 0`. Everyone
  else keeps the exact original filters — rejected loosening the filters
  for the whole league (0026's original reasoning, that every non-pitcher
  gets a same-shaped placeholder row in the raw export, still holds for
  the non-TWP majority; ingesting a placeholder row for every position
  player in the league would reintroduce exactly the bloat 0026 filtered
  out).
- **`role_group` for a TWP: a new, distinct `'TWP'` group, not `'SP'`/
  `'RP'`/a lookback.** **Chosen (confirmed with the user):** most
  explicit — visually calls out two-way players as their own category
  in the depth chart rather than filing them under a pitcher role that
  may not reflect that month's actual usage.
- **Projection math for a `role = 0` heap: default to `'SP'`
  `role_constants`.** Ingesting the row alone isn't enough —
  `PitcherProjection.__init__`'s `ROLE_MAP` (`pitcher.py`) had no entry
  for role `0` and would raise `ValueError` (caught per-player by
  `process_pitcher`, logged and skipped, not a crash — but it meant no
  `players_pitching_run_value` row, so no pitching WAR, for that month).
  **Chosen (confirmed with the user):** add `0: 'SP'` to `ROLE_MAP` —
  same "default an unrecognized/absent role to Starter, more
  conservative" precedent [0059](0059-wire-injury-risk-into-surplus-value.md)
  already established for its injury-discount multiplier — so a TWP's
  `role = 0` months still produce a real projected pitching WAR from
  their actual stuff/control/etc. ratings, not silence.
- **Downstream "never net batting/pitching WAR, exclude two-way
  entirely" precedent — confirmed out of scope for this ticket.**
  [0056](0056-surplus-value-calculation.md)'s surplus-value calculation
  and [0063](0063-roster-depth-chart-query-api.md)'s depth-chart query
  both treat a player with both batting and pitching WAR present as
  `war = NULL` / excluded outright, rather than guessing how to combine
  them. Once TWP pitching data stops silently disappearing, more players
  will hit this branch more consistently (rather than intermittently).
  Left as-is — flagged for whoever picks up real two-way value
  combination next, not resolved here.
- **Pitch repertoire (0029/0031/0032) left unfixed, deliberately.**
  `migration_short.sql`'s `players_pitch_repertoire` INSERT has the same
  `role IN (11, 12, 13)` filter, 12 more occurrences across its 12
  pitch-type UNION branches — same shape of gap, but a separate feature
  area not implicated in the reported crash or discussed with the user.
  Not touched here; a natural, cheap follow-up (reuse the same
  `twp_player_ids` temp table) if a TWP's pitch repertoire ever turns out
  to matter somewhere.

## 3. Approach

- `backend/app/db/sql_scripts/migration/migration_short.sql`: added a
  `twp_player_ids` `TEMPORARY TABLE`, populated once per heap run from
  `players_career_batting_stats`/`players_career_pitching_stats` (any
  `PA > 0` and `IP > 0` in `YEAR('{{HEAP_DATE}}')`). The four affected
  `INSERT ... WHERE` clauses (`players_batting`, `players_batting_talent`,
  `players_pitching`, `players_pitching_talent`) now read
  `WHERE r.rating_date = '{{HEAP_DATE}}' AND (<original role condition>
  OR s.player_id IN (SELECT player_id FROM twp_player_ids))`.
- `backend/app/player_projection/pitcher.py`: `ROLE_MAP` gained
  `0: 'SP'`.
- `backend/app/db/sql_scripts/api/get_org_depth_chart.sql`: `role_group`'s
  `CASE pp.role ... ELSE NULL END` changed to `ELSE 'TWP'` — also a
  defensive fix for any other edge case that produces a missing/
  unrecognized role, not just detected TWPs, since a `NULL` role_group
  reaching the Python grouping layer is exactly what crashed 0064.
- `frontend/src/views/TeamDepthChart.vue`: `'TWP'` added to `GROUP_ORDER`
  (sorted last) and `PITCHER_GROUPS` (renders in the right/pitchers
  column alongside SP/RP).

**Verified** on a throwaway MariaDB container (established pattern):
built a minimal schema with three synthetic players modeled on real
profiles — a normal pitcher (`role = 11` always), a normal batter
(`role = 0` always, no pitching career stats), and a TWP modeled on
Eldridge (`role = 0` this heap, real `PA`/`IP` on both sides for the
year). Ran the modified `migration_short.sql` (via the exact
`{{HEAP_DATE}}` substitution the real pipeline uses) against it:
- Normal pitcher: batting excluded, pitching ingested (`role = 11`) —
  unchanged.
- Normal batter: batting ingested, pitching excluded — unchanged.
- TWP: **both** batting and pitching ingested, `role = 0` correctly
  carried through into `ootp.players_pitching` (previously would have
  had no row at all).
- Confirmed `get_org_depth_chart.sql`'s updated `CASE` resolves
  `role_group = 'TWP'` for the TWP, `'SP'` for the normal pitcher
  unchanged, and (harmlessly, since it's ignored for non-`'P'` positions
  downstream) `'TWP'` for the normal batter too.
- Backend suite: 129 passed (no existing tests reference the changed SQL
  directly — `test_teams.py`'s depth-chart tests mock rows at the Python
  layer, unaffected by the SQL-layer change; `pitcher.py` has no existing
  unit tests to extend, matching this project's existing coverage gap for
  that module — verified via the throwaway-DB pipeline run instead).
  Frontend: Vite HMR recompiled cleanly, `npx vue-tsc -b` unchanged from
  the 34-error baseline.

## Post-implementation correction: detection query used the wrong year

The user ran a full reprocess of the save (`init-db` + `update-db` from
scratch) to apply the fix. Result checked against the live dev DB:
Eldridge's December 2029 `players_pitching` row was still missing —
`twp_player_ids` had found nobody.

**Root cause:** `migration_short.sql` processes a given calendar year's
monthly heaps (01–12) *before* that same year's yearly heap — confirmed
via `processed_heaps.processed_at` timestamps on the live DB (months
01–12 for 2029 all processed before "2029 yearly"). The yearly heap is
what actually writes that year's rows into `players_career_batting_
stats`/`players_career_pitching_stats` (it captures the just-completed
season). So `twp_player_ids`' original condition
(`cb.year = YEAR('{{HEAP_DATE}}')`) was checking for 2029 data while
processing a 2029 monthly heap — data that doesn't exist yet at that
point in the run, every time. Confirmed on the live DB after the user's
full reprocess completed (once the yearly heap had also run):
`players_career_batting_stats`/`_pitching_stats` do have real 2029 rows
for Eldridge (`PA = 569`, `IP = 8`) — the detection logic itself was
sound, just looking at the wrong year during the run that actually
needed it.

**Fixed:** `twp_player_ids` now checks `cb.year = YEAR('{{HEAP_DATE}}')
- 1` (the previous year) instead — always already populated by the time
any heap for the current year runs, since last season already concluded.
Confirmed Eldridge has real, consistent two-way usage every year back to
2023 (`players_career_batting_stats`/`_pitching_stats` both have PA > 0/
IP > 0 for 2023–2029), so using last year as the signal is a good proxy
for "is this player a TWP now" in practice — the only real gap is a
player becoming a TWP for the very first time this season, who wouldn't
be detected until next year's monthly heaps. Not solvable without also
reordering yearly-before-monthly processing for the same year, which is
out of scope here.

Re-verified on a fresh throwaway DB with the corrected query (career
stats seeded for 2028, not 2029, matching real pipeline timing): Eldridge
correctly gets both `players_batting` and `players_pitching` ingested for
his December 2029 heap, `role = 0` carried through as before. Backend
suite: 129 passed.

**Still not yet applied to the persistent dev-stack `ootp` database** —
awaiting another reprocess with this correction. Same caveat as before:
`update-db` only processes *new* heaps (`processed_heaps`, ticket 0007),
so an already-ingested heap needs to be forced to reprocess (or, as the
user did last time, a full `init-db` + `update-db` from scratch) for the
fix to actually reach the 11 currently-broken orgs.

**Files involved:**
- `backend/app/db/sql_scripts/migration/migration_short.sql` (modified,
  then corrected — `twp_player_ids`' year offset)
- `backend/app/player_projection/pitcher.py` (modified — `ROLE_MAP`)
- `backend/app/db/sql_scripts/api/get_org_depth_chart.sql` (modified —
  `role_group` default)
- `frontend/src/views/TeamDepthChart.vue` (modified — `'TWP'` group)

## Post-implementation addition: show "TWP" on the player page

**User-requested:** the player detail page should also show "TWP" as a
two-way player's position, not just the depth chart.

**Fixed:**
- `get_player_details.sql`: added `is_twp` (a boolean `EXISTS` check —
  real `PA > 0` and `IP > 0` in the same year, checked against the
  player's own most recent recorded career-batting year, not a hardcoded
  year offset — this runs at request time, not tied to heap-processing
  order the way `migration_short.sql`'s pipeline-timing-constrained
  version of this same check is). `p.position` itself is left untouched —
  it still drives `PlayerDetails.vue`'s batting/pitching table visibility
  and `PlayerProfile.vue`'s `BatterPercentiles`/`PitcherPercentiles`
  selection elsewhere; `is_twp` is a separate, purely-display flag.
- `PlayerDetails.vue`: the position line now renders
  `playerDetails.is_twp ? 'TWP' : playerDetails.position`.

**Noticed, not fixed (out of scope for this request):** a TWP's
`position` is still `'P'` everywhere else, so `PlayerDetails.vue`'s
batting table (gated `position !== 'P'`) still doesn't render for them,
even though they have real batting stats — only the position *label*
changed. Worth a follow-up if/when someone wants the full page (not just
the header) to reflect two-way status.

**Verified:** direct SQL check against the live dev DB — Eldridge
(43866) returns `is_twp = 1`; a normal position player (Corbin Carroll,
23790) returns `is_twp = 0`. Live API: `GET /api/players/43866/details`
returns `is_twp: true` with `position` unchanged (`"P"`). Backend suite:
129 passed (no test needed updating — the route just `jsonify(row)`s the
whole row with no explicit key access, so mocked test rows are
unaffected by the new column). Frontend: Vite HMR recompiled cleanly,
`npx vue-tsc -b` unchanged from the 34-error baseline, live page load at
`/players/43866` returns 200.

**Files involved (addendum):**
- `backend/app/db/sql_scripts/api/get_player_details.sql` (modified —
  `is_twp`)
- `frontend/src/components/PlayerDetails.vue` (modified — position label)

## Post-implementation addition: both career-stat tables and tabbed percentiles for TWPs

**User-requested:** the exact gap flagged as "noticed, not fixed" above
— a TWP's page should show both batting and pitching career stats, and
let the user tab between Batting and Pitching percentiles instead of
only ever showing Pitcher (driven by `position === 'P'`).

**Fixed:**
- `PlayerDetails.vue`: the batting-stats fetch (`onMounted`) and the
  Career Batting Stats table's `v-if` both now also trigger when
  `playerDetails.is_twp` is true, alongside the existing
  `position !== 'P'` condition — a TWP's `/career/batting` endpoint
  already returns real data (200, not 404, confirmed live for Eldridge),
  it just wasn't being fetched. The pitching side needed no change —
  `position === 'P'` already covers a TWP.
- `PlayerProfile.vue`: added `isTwp` (reads `playerDetails.is_twp`). When
  true, renders a `TabGroup` (Headless UI, same pattern as
  `TeamDepthChart.vue`'s level tabs) with "Batting"/"Pitching" tabs, each
  panel holding the existing `BatterPercentiles`/`PitcherPercentiles`
  component unchanged. Non-TWP players keep the original single-component
  `position === 'P' ? Pitcher : Batter` behavior, now as an
  `v-else-if`/`v-else` fallback under the new TWP branch.
  `PitchRepertoire` needed no change — already gated on
  `position === 'P'`, which correctly includes TWPs already.

**Verified** against the live dev DB: `GET /api/players/43866/career/
batting` and `.../career/pitching` both return 200 for Eldridge (both
tables now render on his page). Vite HMR recompiled cleanly, live page
load at `/players/43866` (TWP) and `/players/23790` (normal player,
unaffected) both return 200, `npx vue-tsc -b` unchanged from the
34-error baseline. Backend suite: 129 passed (no backend logic changed
in this addition beyond what the previous `is_twp` addendum already
covered).

**Files involved (addendum):**
- `frontend/src/components/PlayerDetails.vue` (modified again — fetch +
  table visibility for both stat sides)
- `frontend/src/views/PlayerProfile.vue` (modified — tabbed Batting/
  Pitching percentiles for TWPs)

## Post-implementation correction: pitch repertoire was never fixed for TWPs

**User-reported:** for a TWP, Pitch Category Percentiles, Pitching Stats,
and Pitch Repertoire all appeared not to render.

**Root cause, confirmed live:** `players_pitch_repertoire` had zero rows
for Eldridge's rating (`GET /api/players/ratings/1066287/pitch_repertoire`
→ `[]`) — this is exactly the gap this ticket's own Design choices
section explicitly flagged and *deliberately* left unfixed
("Pitch repertoire... left unfixed, deliberately... a separate feature
area not implicated in the reported crash"). Once actually exercised by a
real TWP's page, it turned out to matter: `PitcherPercentiles.vue`'s
Value-section pitch-category bars (`fastball_grade_percentile`/
`breaking_grade_percentile`/`offspeed_grade_percentile`, ticket 0034) are
computed from `players_pitch_repertoire` and were `null`;
`PitchRepertoire.vue` correctly rendered its "No repertoire data
available" empty state (confirmed by reading the component — it's not
silently blank, just genuinely empty). "Pitching Stats" specifically
wasn't reproducible: direct API checks confirmed real data for both the
Career Pitching Stats table (`/career/pitching`) and the percentile bars
(`era_percentile`, `stuff_percentile`, etc. all populated, not null) with
unchanged/correct gating logic — flagged to the user as unconfirmed,
possibly stale from viewing the page before an earlier fix's reprocess
had landed.

**Fixed:** extended the same `twp_player_ids` carve-out (already used for
`players_batting`/`players_pitching`) to all 12 pitch-type branches of
`players_pitch_repertoire`'s `UNION ALL` INSERT — each branch's
`WHERE ... AND s.role IN (11, 12, 13) AND s.pitching_ratings_pitches_X >
0` becomes `WHERE ... AND (s.role IN (11, 12, 13) OR s.player_id IN
(SELECT player_id FROM twp_player_ids)) AND s.pitching_ratings_pitches_X
> 0`.

**Verified** on a throwaway DB (same synthetic-player pattern as this
ticket's earlier corrections, extended with real fastball/slider grades
for both a normal pitcher and a TWP): both correctly get
`players_pitch_repertoire` rows now; the normal pitcher's ingestion is
unaffected. Backend suite: 129 passed.

**Not yet applied to the persistent dev-stack `ootp` database** — the
user will run the reprocess themselves.

**Files involved (addendum):**
- `backend/app/db/sql_scripts/migration/migration_short.sql` (modified
  again — TWP carve-out extended to all 12 `players_pitch_repertoire`
  branches)

## Post-implementation layout change: pitch repertoire moved under pitcher percentiles

**User-requested:** move `PitchRepertoire` out of the left column (under
`PlayerDetails`) to sit under `PitcherPercentiles` instead; for a TWP,
only render it while the "Pitching" tab is selected.

**Fixed:** `PlayerProfile.vue` — `PitchRepertoire` removed from the left
column entirely. For a non-TWP pitcher, it now renders directly below
`PitcherPercentiles` inside that branch's own wrapping `flex flex-col`
div. For a TWP, it renders inside the "Pitching" `TabPanel`, below
`PitcherPercentiles` — no extra visibility logic needed for the
tab-gating requirement, since Headless UI's `TabPanel` only mounts the
active panel's content by default (confirmed via the library's
documented behavior — inactive panels unmount, not just hide via CSS),
so it naturally only renders while that tab is selected.

**Verified:** Vite HMR recompiled cleanly, live page loads for a TWP
(43866) and a normal pitcher (158) both return 200, `npx vue-tsc -b`
unchanged from the 34-error baseline.

**Files involved (addendum):**
- `frontend/src/views/PlayerProfile.vue` (modified — `PitchRepertoire`
  relocated)

## Post-implementation correction: depth-chart TWP detection missed players whose position isn't 'P'

**User-reported:** Shohei Ohtani's player page correctly shows TWP, but
on the LAD org depth chart he's tagged `DH`.

**Root cause, confirmed live:** `players.position` for Ohtani is `'DH'`,
not `'P'` — but he has a real `players_pitching` row (his latest
snapshot, Dec 2029, reads `role = 0`; an earlier one read `role = 11`,
Starting Pitcher). `get_org_depth_chart.sql`'s `role_group` (SP/RP/TWP)
logic only ever gets consulted when `position == 'P'`
(`app/api/teams.py`'s grouping line) — a real two-way player whose
listed position happens to be a batting position was silently filed
under that position with his pitching side completely invisible in the
depth chart, even though `get_player_details.sql`'s identical `is_twp`
check already correctly flagged him as TWP on his own player page. Two
different, disagreeing definitions of "is this player TWP" (one gated on
`position == 'P'`, one based on real career PA/IP evidence) had been
built for the same concept.

**Fixed:** added the exact same `is_twp` `EXISTS` check (real `PA > 0`
and `IP > 0` in the player's own most recent recorded career-batting
year) already used in `get_player_details.sql` to
`get_org_depth_chart.sql`'s output. `app/api/teams.py`'s grouping now
checks `is_twp` first, before `position`: `'TWP'` if `is_twp`, else the
existing `role_group`-if-`position == 'P'`-else-`position` logic. The
depth chart and the player page now always agree.

**Verified:** SQL run directly against the live dev DB for Ohtani
(33695) — `is_twp = 1`, `role_group = 'TWP'` (his latest snapshot reads
`role = 0`), `war = NULL` (both batting and pitching WAR now genuinely
present — `players_run_value.WAR = 3.87`, `players_pitching_run_value.
WAR = 2.29` — correctly hits the existing never-net-two-way-WAR
exclusion, not a bug). Live API after a backend restart: `GET
/api/teams/15/depth-chart` places him under the `TWP` group; the `DH`
group no longer contains him at all. Backend suite: 130 passed
(1 new test: `test_get_team_depth_chart_twp_groups_by_twp_even_when_
position_not_pitcher`, modeled directly on this real case). Frontend
type-check unchanged from the 34-error baseline (no frontend code
changed — `'TWP'` was already a recognized group from the earlier
correction).

**Files involved (addendum):**
- `backend/app/db/sql_scripts/api/get_org_depth_chart.sql` (modified
  again — `is_twp` column)
- `backend/app/api/teams.py` (modified again — grouping checks `is_twp`
  first)
- `backend/tests/api/test_teams.py` (modified — new test + `is_twp` field
  on the row fixture)

## Post-implementation change: depth-chart TWP WAR sums both sides

**User-requested:** for the depth chart, a TWP's projected WAR should be
the sum of batting and pitching WAR, not `null`.

**Fixed:** `get_org_depth_chart.sql`'s `roster_war` and `league_level_war`
CTEs both changed `WHEN brv.WAR IS NOT NULL AND prv.WAR IS NOT NULL THEN
NULL` to `THEN brv.WAR + prv.WAR`. Scoped to the depth chart only —
[0056](0056-surplus-value-calculation.md)'s surplus-value calculation and
`contract_value.py` still exclude two-way players entirely (unchanged,
per their own established precedent; this request was specifically about
the depth chart's display). `league_level_war` (the AAA/AA promotion-
candidate comparison pool) got the same change for consistency, so a rare
TWP at that level is compared on the same basis as everyone else instead
of silently excluded from the pool.

**Verified** live: `GET /api/teams/15/depth-chart` now shows Ohtani's
`war: 6.1537` — exactly his batting WAR (3.86627) plus pitching WAR
(2.28742). Backend suite: 130 passed (pure SQL-layer change, no Python
logic touches the `war` value — `app/api/teams.py` just passes it
through, so no test changes needed). Caught and fixed a real semicolon-
inside-a-SQL-comment while writing this (ticket 0055's class of bug) in
my own new comment text before it could cause any actual harm.

**Files involved (addendum):**
- `backend/app/db/sql_scripts/api/get_org_depth_chart.sql` (modified
  again — WAR summing for two-way players)
- `backend/app/api/teams.py` (modified again — docstring only)

## Post-implementation correction: pitching career stats still gated on position === 'P'

**User-reported:** Ohtani's page still doesn't show his Pitcher Career
stats.

**Root cause:** the exact same class of bug as the depth-chart grouping
fix above, just in `PlayerDetails.vue` instead — the pitching-stats
fetch and its table's `v-if` were both still gated purely on
`position === 'P'`, which I'd assumed "already covers TWPs" when adding
the batting-side fix earlier in this ticket. True for a TWP whose
listed position happens to be `'P'` (e.g. Eldridge), false for one whose
position is a batting position (Ohtani is `'DH'`) — his pitching fetch
never ran and the table never showed, mirroring the exact gap the
`is_twp`-first depth-chart fix above just closed for grouping.

**Fixed:** both the pitching-stats fetch (`onMounted`) and the Career
Pitching Stats table's `v-if` in `PlayerDetails.vue` now also trigger on
`playerDetails.is_twp`, alongside the existing `position === 'P'`
condition — same fix shape as the batting side already had.

**Verified:** `GET /api/players/33695/career/pitching` returns real data
(21 GS, 122 K in 2029, etc.) — confirmed the endpoint itself was never
the problem, only the frontend gate. Vite HMR recompiled cleanly, live
page load at `/players/33695` returns 200, `npx vue-tsc -b` unchanged
from the 34-error baseline.

**Files involved (addendum):**
- `frontend/src/components/PlayerDetails.vue` (modified again — pitching
  fetch + table visibility also check `is_twp`)

## Post-implementation change: Surplus Value now available for TWPs

**User-reported:** TWPs don't render Surplus Value.

**Root cause:** `app/api/players.py`'s `/surplus-value` route excluded
any player with both `batting_war` and `pitching_war` present outright
(`two_way` check) — ticket 0056's original never-net-batting/pitching-WAR
precedent. Confirmed live: `GET /api/players/33695/surplus-value` →
`{"available": false}`.

**Chosen (confirmed with the user):** extend the exact same treatment
just applied to the depth chart — sum batting + pitching WAR into a
single `base_war` for the whole multi-year projection, rather than
excluding the player. A deliberate, explicit override of 0056's original
precedent for this route specifically (not `contract_value.py`'s
underlying function itself, which still just takes whatever `base_war`
it's given — no change needed there).

**Fixed:**
- `app/api/players.py`: the `two_way`-excludes-entirely check is gone;
  `base_war = batting_war + pitching_war` when both are present, single
  side otherwise.
- The injury-durability lookup (`is_pitcher` passed to
  `calculate_surplus_value`) now reads `pitching_war is not None and
  batting_war is None` — a TWP uses the batter durability multiplier, not
  the pitcher one, since their primary defensive workload (games played/
  batted) is typically far larger than their pitching innings share as a
  share of playing time.

**Verified** live: `GET /api/players/33695/surplus-value` now returns
`available: true`, `war: 6.15369` for every projected year — exactly
batting WAR (3.86627) + pitching WAR (2.28742), matching the depth
chart's sum exactly. Real contract/cost data flows through unchanged.
Replaced the old `test_get_player_surplus_value_two_way_not_available`
test with `test_get_player_surplus_value_two_way_sums_war`, asserting the
summed value directly. Backend suite: 130 passed (net-neutral test
count — one test replaced, not added). Frontend: `SurplusValue.vue`
needed no change (already just renders whatever the API returns), live
page load at `/players/33695` returns 200, `npx vue-tsc -b` unchanged
from the 34-error baseline.

**Files involved (addendum):**
- `backend/app/api/players.py` (modified again — TWP WAR summed instead
  of excluded)
- `backend/tests/api/test_players.py` (modified — replaced the two-way-
  excluded test with a two-way-sums-WAR test)

## Post-implementation correction: fielding arm/range percentiles missing for a TWP whose listed position is 'P'

**User-reported:** Bryce Eldridge doesn't render fielding range and arm
percentiles.

**Root cause:** `players.position` for Eldridge is `'P'`, not a real
fielding position — but he has real fielding grades in
`players_fielding_position` (RF 60, 1B 50, LF 35). `get_player_expected_
fielding_percentiles.sql` classifies `position_group` purely from
`players.position`, and `'P'` falls through every branch to `'other'`,
so `fielding_value`/`fielding_value_percentile` and every arm/range
percentile came back `NULL` — confirmed live before the fix. The same
underlying limitation as the depth-chart-grouping and career-pitching-
stats bugs above (a TWP's single `players.position` field can't capture
both sides of what they actually do), now showing up a third time, in a
third feature.

**Fixed:** `target_player` derives an `effective_position` — for a
player whose `position = 'P'`, the highest-graded non-pitcher slot from
`players_fielding_position` (via `GREATEST()`/`CASE`, not a derived
table — MariaDB can't correlate a FROM-clause derived table against an
outer column without `LATERAL`, an approach tried first and rejected
after it failed with `Unknown column 'pr.rating_id' in 'WHERE'`); for
everyone else, their own `position` unchanged. `effective_position`
drives `position_group` and the `fielding_value` lookup from
`players_fielding_expected`; the `cohort`/`catcher_cohort`/
`infielder_cohort`/`outfielder_cohort` CTEs are deliberately left
unchanged (still built from real `players.position` membership, not
reclassifying other TWPs) — scoped to correcting the *target's own*
comparison group, not cohort composition, matching this project's
existing convention of treating cohort-membership changes as their own
careful decision (0037, 0060). The API's `position` output field itself
is untouched — still `'P'` for Eldridge, consistent with every other
feature keyed off `players.position`.

**Verified** directly against the live dev DB: Eldridge's rating
(1066287) now returns `position_group: "outfield"`, `fielding_value:
2.42682` (79th percentile), `outfield_arm_percentile: "93"`,
`outfield_range_percentile: "41"` — `position` stays `"P"`. Confirmed a
real one-way pitcher (Zac Gallen, 1064912) is unaffected (still no row,
same as before — pure pitchers never had fielding percentiles, no
regression). Confirmed a normal position player (1B, 1075212) is
byte-for-byte unchanged. Backend suite: 130 passed (no existing test
touches this query's SQL directly). Live API call after a backend
restart matches the direct-SQL check exactly. Frontend: page load at
`/players/43866` returns 200, `npx vue-tsc -b` unchanged from the
34-error baseline (no frontend code changed — `BatterPercentiles.vue`
already just renders whatever the API returns).

**Files involved (addendum):**
- `backend/app/db/sql_scripts/api/get_player_expected_fielding_percentiles.sql`
  (modified — `effective_position` derivation for a TWP whose listed
  position is `'P'`)
