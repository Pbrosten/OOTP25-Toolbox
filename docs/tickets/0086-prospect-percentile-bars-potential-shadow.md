# 0086 — Prospect percentile bars + current-vs-potential shadow

- **Tag:** feat
- **Status:** In-Progress
- **Depends on:** —
- **Blocks:** —

## 1. Problem

`BatterPercentiles.vue`/`PitcherPercentiles.vue` explicitly gate all
percentile bars behind `isMlb` (`leagueId === 203`): a prospect gets
`"Percentile comparisons are only available for MLB players."` and
nothing else, no matter how advanced or MLB-ready they are. Every other
prospect-facing view (`ProspectPipeline.vue`, `TeamDepthChart.vue`,
`ProspectLeaderboard.vue`) already shows FV grade/expected WAR for
players who haven't reached the majors — percentile bars are the one
piece of the per-player detail page prospects can't get.

Separately, `PercentileBar.vue` (the shared bar component both pages use)
only ever renders a single "current" value per skill. The schema already
stores a current/potential (talent) pairing for most rated skills —
`players_batting_talent`/`players_pitching_talent`/
`players_fielding_position_talent`, plus `players_pitch_repertoire.
talent_grade` — but today the only place any of that potential data is
even shown is `PitchRepertoire.vue`'s bare "Potential" table column.
There's no visual "how much higher could this go" indicator anywhere,
which is exactly what a scouting-style percentile bar should show for a
player who hasn't peaked yet — most relevant for prospects, but also true
for young MLB players still short of their ceiling.

## 2. Design choices

- **Resolved 2026-08-16 — population to percentile-rank prospects
  against.** Verified directly: every `get_player_expected_*_percentiles.
  sql` script (`backend/app/db/sql_scripts/api/`) already filters its
  comparison population by `r.league_id = t.league_id` — a prospect is
  already compared against *other players in their own league*, not MLB.
  And `app/db/update.py` runs `process_player`/`process_pitcher`
  (→ `BatterProjection`/`PitcherProjection`) over every ingested player
  every heap, with no MLB-only filter — `players_batting_expected`/
  `players_run_value` rows already exist for prospects today. The `isMlb`
  frontend gate in `BatterPercentiles.vue`/`PitcherPercentiles.vue` was
  simply never relaxed once the backend could support it, not a real
  calibration blocker. **No new backend population/comparison work is
  needed** — this half of the ticket is a frontend gate change plus
  verifying the percentiles render sensibly end-to-end for a real
  prospect `rating_id`.
- **Resolved with the user 2026-08-16 — how to compute the "potential"
  value for the shadow.** Re-run the expected-stat projection with talent
  grades substituted for current grades, not a raw-grade-gap
  approximation. Confirmed feasible directly against `BatterProjection.
  __init__` (`backend/app/player_projection/batter.py:43-81`): it reads
  `data.get('babip'/'gap'/'eye'/'power'/'strikeouts')` — the exact same
  column names `players_batting_talent` uses — plus `speed`/`steal`/
  `baserunning` (no talent table exists for these, see the basepath note
  below) and `pos2`–`pos9` defense grades (`players_fielding_position_
  talent` does have a ceiling counterpart for these). A "potential" run is
  just the same `data` dict with the battable/fieldable talent columns
  swapped in, fed through the same `calc_expected_stats()`. Same shape
  for `PitcherProjection`. This needs no fundamentally new logic, just a
  second invocation with different inputs.
- **Resolved with the user 2026-08-16 — shadow scope.** Applies to all
  percentile bars, not prospects only — `PercentileBar.vue` is shared by
  both `BatterPercentiles.vue` and `PitcherPercentiles.vue`, and a young
  MLB player short of their ceiling gets the same shadow treatment as a
  prospect. No prospect-only conditional needed.
- **`players_basepath` has no talent-grade counterpart in `schema.sql`**
  (no ceiling data for speed/steal/baserunning). The Base Running
  percentile category can never get a shadow value under any option
  above — bars in that category would just never show one, which is
  fine, not a blocker, noting it so it isn't mistaken for a bug later.

## 3. Approach

1. **Persist a "potential" projection alongside the existing one.** At
   ingestion time (`app/db/update.py`'s `process_player`/`process_pitcher`,
   `app/db/projection.py`), also run `BatterProjection`/`PitcherProjection`
   a second time per rating with talent grades substituted for current
   grades (batting: babip/gap/eye/power/strikeouts from
   `players_batting_talent`; pitching: the equivalent
   `players_pitching_talent` columns; fielding: `players_fielding_
   position_talent`; basepath ratings stay as current values — no talent
   table exists for speed/steal/baserunning). Persist the result into new
   `_talent`-suffixed tables mirroring the existing expected/run-value
   tables (e.g. `players_batting_expected_talent`,
   `players_run_value_talent`), same `INSERT IGNORE ... rating_id` pattern
   as the current ones.
2. **Extend the percentile SQL scripts** (`get_player_expected_*_
   percentiles.sql`) to also return each stat's potential percentile,
   ranked against the same `league_id`-scoped comparison group's *current*
   values (i.e. "if this player reached their ceiling today, where would
   they rank against today's league"), plus the raw potential value
   alongside the existing raw current value.
3. **Frontend:** `PercentileBar.vue` renders a second, lighter/shadow fill
   from the current percentile out to the potential percentile, only when
   potential > current. `BatterPercentiles.vue`/`PitcherPercentiles.vue`
   drop the `isMlb` gate (percentiles already work for any league per the
   Design choices above) and pass both values through to each bar.

**Files involved:**
- `backend/app/db/sql_scripts/schema.sql` (modified — 5 new `_talent`
  expected/run-value tables: `players_batting_expected_talent`,
  `players_fielding_expected_talent`, `players_run_value_talent`,
  `players_pitching_expected_talent`, `players_pitching_run_value_talent`.
  No `players_basepath_expected_talent` — basepath has no talent grades).
- `backend/app/db/sql_scripts/migration/get_projection_inputs.sql`,
  `get_pitcher_projection_inputs.sql` (modified — join the `_talent`
  rating tables, expose `t_*`-prefixed ceiling grades).
- `backend/app/db/projection.py` (modified — `process_player`/
  `process_pitcher` each run `BatterProjection`/`PitcherProjection` a
  second time with `t_*` grades substituted in, in an isolated
  try/except so a potential-projection failure doesn't drop the
  player's real current-rating result; new `proj_scripts`/
  `pitching_proj_scripts` entries for the `_talent` tables).
- `backend/app/db/update.py` (modified — `insert_projections()`/
  `insert_pitcher_projections()`'s batch-key lists extended for the new
  `_talent` projection keys).
- `backend/app/db/sql_scripts/api/get_player_expected_batting_
  percentiles.sql`, `get_player_expected_value_percentiles.sql`,
  `get_player_expected_fielding_percentiles.sql`, `get_player_expected_
  pitching_percentiles.sql` (modified — each `*_percentile`/raw-value
  column gets a `*_percentile_potential`/`*_value_potential` (or
  `<name>_potential`, matching the source column's own naming)
  counterpart, ranked against the *same* current-population CTE via a
  `LEFT JOIN` to the relevant `_talent` table. `get_player_expected_
  basepath_percentiles.sql` deliberately untouched — no talent data
  exists for those grades). `backend/app/api/projections.py` needed no
  changes — every route already does a generic `jsonify(row)`.
- `frontend/src/components/percentiles/PercentileBar.vue` (modified —
  new optional `potentialPercentile` prop; renders a shadow fill
  (`bg-gray-500/40` + inset box-shadow) from the current percentile out
  to the potential one, only when potential > current).
- `frontend/src/components/percentiles/BatterPercentiles.vue`,
  `frontend/src/components/percentiles/PitcherPercentiles.vue` (modified
  — dropped the `isMlb` gate entirely (always fetch/render percentiles
  regardless of league); added a `getPotentialPercentile()` helper that
  mechanically looks up `${key}_potential` on the API response and wires
  it into every `<PercentileBar>`, except the Base Running group (no
  potential data, so left unwired)).

**Verified:** `schema.sql` loads cleanly on a throwaway MariaDB container
(established pattern, no persistent volume — not run against the real
`ootp` database). All 4 modified percentile SQL scripts and both modified
migration input queries execute without error against that empty schema
(syntax/reference check). `process_player`/`process_pitcher` exercised
directly with synthetic current vs. elite (grade 80) talent input:
current-grade batter projected 1.6 WAR, the same inputs with grade-80
ceiling ratings projected 13.0 WAR; pitcher ERA dropped from 4.60 to 1.92
and WAR rose from 1.33 to 9.19 — correct direction on both. Frontend
picked up every change via Vite HMR with no errors. Not verified: a real
ingested heap end-to-end (needs a real dump + `update-db` run, not done
this session), and no visual/browser check (no browser tool available).
