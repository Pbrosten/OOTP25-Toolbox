# 0066 — Recalibrate run-value constants against this save's own league, not a fixed real-MLB baseline

- **Tag:** fix
- **Status:** Closed
- **Depends on:** —
- **Blocks:** —

## 1. Problem

Reported directly: Kyle Manzardo (player 45014, active MLB roster, White
Sox) shows a *negative* Batting Run Value (-2.9) alongside a *73rd*
percentile — a below-average raw number reading as a well-above-average
percentile bar, which looks like a bug.

Investigated against the live `TEST.lg` save. The percentile calculation
itself is correct and its cohort isn't polluted by the administratively-
parked-player contamination [0064](0064-roster-depth-chart-frontend.md)
found and fixed elsewhere (verified: `get_player_expected_value_
percentiles.sql`'s cohort for Manzardo's rating snapshot is 607 players,
all with `is_active = 1` on `players_service_time` — zero parked/inactive
contamination). `440/607` of that cohort have `batting_runs` below
Manzardo's -2.9, giving exactly `73%` — the displayed number is the
correct percentile of the correct cohort.

**The real cause:** `batting_runs` (`app/player_projection/batter.py:226`,
`wRAA = ((wOBA - LG_WOBA) / FACTOR_WOBA) * PA`) is computed against
`LG_WOBA = 0.325`, a **fixed constant sourced from the real-MLB rate
tables the projection methodology's source spreadsheet was built from**
— not this save's own league average, despite "wRAA" (weighted Runs
*Above Average*) meaning "above the player's own league's average" by
definition in real sabermetrics. Confirmed via real data: the median
`batting_runs` among this save's actual active-roster MLB position
players (607 players, league_id 203, age ≥ 22, `is_active = 1` —
i.e. the real thing, not org depth) is **-9.14**, and only 123/607 (20%)
are non-negative. A below-real-MLB-average hitter can still be
well above-average *for this specific save's diluted talent pool* — this
save has 34 "MLB" teams (not the real 30), so per-team talent is more
diluted than a real MLB roster, a known finding from
[0058](0058-contract-recommendation-thresholds.md)'s investigation (259
teams total, most rated players are organizational depth) — this ticket
confirms the same dilution effect reaches even the genuinely active
26-man-roster population, not just unfiltered org depth. The percentile
(relative to this save's own population) and the raw value (relative to
real MLB) are each individually correct on their own terms, but
showing them side-by-side with no shared reference frame reads as
contradictory.

The identical pattern exists on the pitching side —
`pitcher.py`'s `pitching_runs` is computed from `LG_PWOBA = 0.327` and
`RA9_BASELINE = 4.65`, both likewise fixed real-MLB constants
(`pitcher.py:156-157`) — not reported directly, but the same root cause
applies symmetrically and should be fixed together.

**Chosen (confirmed with the user):** recalibrate the run-value baseline
constants to be derived from this save's own league-average performance
per heap, rather than hardcoded real-MLB numbers — the more correct fix,
not just a UI-level clarification, even though it's a bigger change (same
category of scope as [0026](0026-pitcher-projection-methodology.md)).

## 2. Design choices

- **Resolved with the user 2026-08-17 — which constants get
  recalibrated.** Targeted only: `LG_WOBA` (batting) and `LG_PWOBA`/
  `RA9_BASELINE` (pitching) — these directly gate the reported symptom
  since `wRAA`/`runs_prevented` are defined in terms of a league average.
  `RUNS_WIN`/the pitching runs-per-win blend stay fixed — they only scale
  WAR's magnitude uniformly, not rankings/percentiles, so they don't
  affect the reported bug either way.
- **Resolved with the user 2026-08-17 — source data and cadence.**
  Recomputed once per **long/yearly heap** (not every short heap), from
  a **rolling 3-season pooled window of real per-season box-score
  totals** — `players_career_batting_stats`/`players_career_pitching_
  stats` (already ingested in full by `migration_long.sql` every long
  heap) — not from this save's rating-derived *projections*. Using real
  outcomes (not our own projected wOBA) avoids a circular calibration
  (calibrating the projection formula's baseline off its own projected
  output) and matches how real sabermetric league-average constants are
  actually derived each season. Applies uniformly to every projection
  (any league/level) until the next long heap recomputes it — mirrors
  how a real AAA/prospect player's wRAA is legitimately compared against
  the *MLB* league average in real sabermetrics, not a lower-level one.
- **Resolved with the user 2026-08-17 — window and pooling.** The 3 most
  recently-ingested distinct `year`s present for `league_id = 203` (not
  a `heap_date`-relative offset — more robust, and self-limiting to
  however much real history actually exists so far, including a 1- or
  2-season window on the save's first couple of long heaps). Raw
  counting stats (PA/AB/BB/HBP/H/2B/3B/HR for batting; BF/BB/HBP/H
  allowed/HR allowed/RA/outs for pitching) are **pooled** (summed) across
  all 3 seasons first, then a single ratio is computed from the pooled
  totals — naturally volume-weights each season by how much real playing
  time it had, standard practice for a multi-year baseline (vs. simple
  average-of-3-ratios, which would weight a thin season equally to a
  full one).
- **Resolved with the user 2026-08-17 — historical cohort.**
  `players_service_time.is_active`/age floor (ticket 0064's percentile
  cohort) is a *current-roster-only* snapshot with no history — it can't
  filter a prior season's stat line for a player since traded/released/
  retired. Instead: `league_id = 203` plus a minimum-playing-time floor
  per season-row (`PA >= 50` for batting rows, `outs >= 60` i.e. 20 IP
  for pitching rows) to exclude token cameos, computed from `outs`
  (true out count) rather than the `ip` column (OOTP's `6.1`-style
  baseball-notation float isn't safely summable).
- **Formula reuse, not duplicated weights.** The pooled totals are
  converted to `lg_woba`/`lg_pwoba`/`ra9_baseline` in Python using the
  *same* `FACTOR_BB`/`FACTOR_1B`/`FACTOR_2B`/`FACTOR_3B`/`FACTOR_HR`
  weights already defined in `batter.py`/`pitcher.py` (imported, not
  restated) — `lg_pwoba` mirrors `PitcherProjection.calc_rates()`'s own
  simplified wOBA-against formula (`(BB+HBP)*FACTOR_BB + (H-HR)*1 +
  HR*FACTOR_HR`, all non-HR hits weighted 1.0, no 2B/3B split — pitching
  box scores here don't split hits allowed by type anyway), not the
  batting side's fuller weighting. `ra9_baseline = SUM(ra) / (SUM(outs)/3)
  * 9`.
- **Resolved with the user 2026-08-17 — persistence and admin
  visibility.** New `league_baselines` table, one row inserted per long
  heap (history preserved, not overwritten) — `computed_at`,
  `window_start_year`, `window_end_year`, `lg_woba`, `lg_pwoba`,
  `ra9_baseline`, plus sample-size columns (`batting_pa_sample`,
  `pitching_bf_sample`) for the admin display to show how much data
  backed each row. The current value = most recent row. A new
  admin-guarded `GET /api/admin/league-baselines` endpoint (same
  `require_admin_token` pattern as the rest of `app/api/admin.py`)
  surfaces it; `AdminPanel.vue` gets a new read-only section.
- **Fallback for an empty/pre-history state.** Before the first long
  heap ever computes a row (or if the PA/outs floor yields zero
  qualifying rows), `get_projection_inputs.sql`/`get_pitcher_projection_
  inputs.sql` `LEFT JOIN` the latest `league_baselines` row (not
  `CROSS JOIN`) so a missing baseline can't silently zero out every
  projection input row — `BatterProjection`/`PitcherProjection` fall
  back to the existing hardcoded real-MLB constants (`LG_WOBA`/
  `LG_PWOBA`/`RA9_BASELINE` stay as module-level defaults) whenever the
  joined value is `NULL`.
- **Resolved with the user 2026-08-17 — ripple effects into
  already-calibrated downstream constants brought into scope.**
  [0056](0056-surplus-value-calculation.md)'s `WAR_DOLLAR_VALUE` ($8.3M/
  WAR) and [0058](0058-contract-recommendation-thresholds.md)'s
  `RECOMMENDATION_EXTEND_THRESHOLD` ($5M/yr) were both one-time manual
  derivations against real `TEST.lg` contract data under the *old* fixed
  WAR scale — originally deferred here as a follow-up, now folded into
  this ticket so they recalibrate automatically alongside `lg_woba`/
  `lg_pwoba`/`ra9_baseline` instead of going stale the moment this ships.
  Same mechanism, once per long heap: a new `market_baselines` table
  (separate from `league_baselines` — different domain, contract/market
  economics vs. run-value formula constants, and a materially different
  derivation path — Python simulation via `calculate_surplus_value()`,
  not a SQL aggregate), new `compute_market_constants(db)` re-running
  0056's/0058's exact original methodology mechanically:
  - `war_dollar_value` = median implied $/WAR across the same
    "market-rate" cohort 0056 used (current-year salary ≥ $15M, latest
    WAR ≥ 1.5, two-way players skipped — matches 0056's original
    precedent, not the `/surplus-value` route's later TWP-sum deviation,
    which was explicitly scoped to that one endpoint).
  - `recommendation_extend_threshold` = p70 of average-surplus-per-year
    (`total_surplus / years_remaining`), computed by actually running
    `calculate_surplus_value()` over 0058's same curated cohort
    (`years > 0 AND salary0 > $1,000,000`, two-way players skipped),
    using the `war_dollar_value` just computed above in the same pass
    (not the stale hardcoded constant — this cohort's own surplus figures
    depend on it).
  - Both fall back to the existing hardcoded constants when their cohort
    is empty, same empty-state philosophy as `lg_woba`/`lg_pwoba`.
  - **Accepted one-heap lag:** `compute_market_constants` reads whatever
    `players_run_value`/`players_pitching_run_value` already contains at
    long-heap time — last short heap's projections, computed under the
    *previous* `lg_woba`/`lg_pwoba`/`ra9_baseline`, not this heap's
    brand-new one (those tables only refresh on the *next* short heap).
    Not worth blocking this recalibration on a projection re-run that
    hasn't happened yet — `war_dollar_value`/`recommendation_extend_
    threshold` simply catch up one cycle behind `lg_woba`, same as they
    already would in any annual re-derivation process.
  - `contract_value.py`'s `calculate_surplus_value()`/
    `recommend_contract_action()` gain optional trailing `war_dollar_
    value`/`recommendation_extend_threshold` kwargs (default `None` →
    existing module constant — same fallback shape as `BatterProjection`/
    `PitcherProjection`'s `data.get('lg_woba')` pattern), threaded from
    `get_player_contract_inputs.sql`'s new `LEFT JOIN` onto the latest
    `market_baselines` row, through `players.py`'s `/surplus-value`
    route.
  - Admin-visible the same way: new `GET /api/admin/market-baselines`
    endpoint + a second `AdminPanel.vue` section.
- **Outstanding — does the promotion-candidate percentile
  ([0064](0064-roster-depth-chart-frontend.md)) need re-verification?**
  It's rank-based within a level, not tied to the absolute run-value
  scale, so it's likely unaffected — but worth a quick sanity check once
  this ships, not decided here.

## 3. Approach

1. **Schema:** new `league_baselines` table (`id`, `computed_at`,
   `window_start_year`, `window_end_year`, `lg_woba`, `lg_pwoba`,
   `ra9_baseline`, `batting_pa_sample`, `pitching_bf_sample`) — history
   preserved, one row per long heap.
2. **Compute once per long heap:** new `compute_league_baselines(db)` in
   `app/db/update.py` (alongside the other `fetch_*_inputs`/
   `_run_sql_script`-based helpers it reuses), called from
   `process_single_heap`'s long-heap branch right after
   `update_player_age`. Two small
   pooled-aggregate queries (new `.sql` scripts under `db/sql_scripts/
   migration/`) find the 3 most recent `league_id = 203` years present in
   `players_career_batting_stats`/`players_career_pitching_stats` and sum
   the qualifying (`PA >= 50` / `outs >= 60`) rows' raw counting stats.
   Python converts the pooled sums to `lg_woba`/`lg_pwoba`/`ra9_baseline`
   via `batter.py`'s/`pitcher.py`'s existing `FACTOR_*` weights (imported,
   not restated), falling back to the existing hardcoded constants if the
   pool is empty, then inserts the new `league_baselines` row.
3. **Feed it into projections:** `get_projection_inputs.sql`/
   `get_pitcher_projection_inputs.sql` each `LEFT JOIN` the latest
   `league_baselines` row (by `id DESC LIMIT 1`), exposing `lg_woba`/
   `lg_pwoba`/`ra9_baseline` columns on every projection-input row (same
   per-row dict pass-through mechanism ticket 0086 already established for
   the `t_*` talent columns — no `Pool`/multiprocessing signature changes
   needed). `BatterProjection.__init__`/`PitcherProjection.__init__` read
   `data.get('lg_woba')` etc., defaulting to the current module constant
   when `None` (empty-state fallback); `calc_player_values()`/
   `calc_rates()` use `self.lg_woba`/`self.lg_pwoba`/`self.ra9_baseline`
   instead of the bare module constants (both usages of `RA9_BASELINE` in
   `pitcher.py` — `calc_rates()` and the runs-per-win blend in
   `calc_player_values()` — switch together).
4. **Admin visibility:** `GET /api/admin/league-baselines` (guarded by the
   existing `require_admin_token`, same `get_db()`/`close_db()` pattern as
   `app/api/teams.py`) returns the recent history. `frontend/src/api/
   admin.ts` gets a matching fetch function + type; `AdminPanel.vue` gets
   a new read-only section listing each row's window years, the three
   constants, and sample sizes.
5. **Schema (market constants):** new `market_baselines` table (`id`,
   `computed_at`, `war_dollar_value`, `war_dollar_value_sample`,
   `recommendation_extend_threshold`, `threshold_cohort_sample`) —
   separate table from `league_baselines`, same one-row-per-long-heap
   history shape.
6. **Compute once per long heap, right after `compute_league_baselines`:**
   new `compute_market_constants(db)` in `app/db/update.py`, backed by a
   new bulk query `get_market_constants_inputs.sql` (one row per
   `years > 0` contract, latest WAR via a `ROW_NUMBER()` window — the
   many-players equivalent of `get_player_contract_inputs.sql`'s
   single-player `ORDER BY ... LIMIT 1`). Two passes in Python: first
   collects the $/WAR cohort (current-year salary ≥ $15M, WAR ≥ 1.5) to
   compute `war_dollar_value` (`statistics.median`) and caches the
   threshold cohort's raw inputs (`years > 0 AND salary0 > $1,000,000`);
   second pass calls `contract_value.calculate_surplus_value(...,
   war_dollar_value=war_dollar_value)` per cached candidate and takes
   `statistics.quantiles(..., n=10)[6]` (p70) of `total_surplus /
   years_remaining` across the results. Two-way players skipped in both
   passes (`batting_war is not None and pitching_war is not None`).
7. **Feed it into the live endpoint:** `get_player_contract_inputs.sql`
   gains a `LEFT JOIN` onto the latest `market_baselines` row (same
   `ORDER BY id DESC LIMIT 1` pattern as `league_baselines`).
   `calculate_surplus_value()`/`recommend_contract_action()`
   (`contract_value.py`) gain optional trailing `war_dollar_value`/
   `recommendation_extend_threshold` kwargs, `None` → existing module
   constant. `players.py`'s `/surplus-value` route passes the joined
   values through.
8. **Admin visibility:** new `GET /api/admin/market-baselines` endpoint +
   a second `AdminPanel.vue` section, same shape as League Baselines.

**Files involved:**
- `backend/app/db/sql_scripts/schema.sql` (new `league_baselines` +
  `market_baselines` tables).
- `backend/app/db/sql_scripts/migration/get_batting_league_baseline_pool.sql`,
  `get_pitching_league_baseline_pool.sql`, `get_market_constants_inputs.sql`
  (new — pooled 3-season sums, bulk contract/WAR cohort rows).
- `backend/app/db/update.py` (new `compute_league_baselines(db)`,
  `compute_market_constants(db)` + their `fetch_*`/`_run_sql_script`-based
  helpers, both called from the long-heap branch of `process_single_heap`).
- `backend/app/db/sql_scripts/migration/get_projection_inputs.sql`,
  `get_pitcher_projection_inputs.sql` (modified — `LEFT JOIN` latest
  `league_baselines` row).
- `backend/app/db/sql_scripts/api/get_player_contract_inputs.sql`
  (modified — `LEFT JOIN` latest `market_baselines` row).
- `backend/app/player_projection/batter.py`, `pitcher.py` (modified —
  instance-level `lg_woba`/`lg_pwoba`/`ra9_baseline` read from `data`,
  falling back to the existing module constants).
- `backend/app/player_projection/contract_value.py` (modified —
  `calculate_surplus_value`/`recommend_contract_action` gain optional
  `war_dollar_value`/`recommendation_extend_threshold` kwargs, falling
  back to the existing module constants).
- `backend/app/api/players.py` (modified — `/surplus-value` route passes
  the joined market-baseline values through).
- `backend/app/api/admin.py` (new `GET /league-baselines` and
  `GET /market-baselines` routes).
- `frontend/src/api/admin.ts` (new `LeagueBaseline`/`MarketBaseline`
  types + fetch fns).
- `frontend/src/views/AdminPanel.vue` (two new read-only sections).

**Deliberately out of scope:** a sanity re-check of the 0064
promotion-candidate percentile (rank-based, likely unaffected by any of
the above — worth a quick look once this ships, not a code change).

**Verified:** `schema.sql` (including the new `league_baselines` table)
loads cleanly on a throwaway MariaDB container (established pattern, no
persistent volume — not run against the real `ootp` database). Both new
pooled-baseline queries and both modified `get_*_projection_inputs.sql`
queries execute without error against that schema; after seeding one
`league_baselines` row plus one minimal player/rating, confirmed
`lg_woba`/`lg_pwoba`/`ra9_baseline` actually surface through the
`LEFT JOIN`s onto the projection-input rows (not just syntactically
valid). `BatterProjection`/`PitcherProjection` exercised directly with
synthetic data: a lower `lg_woba` raised batter WAR (1.60 → 2.86, same
output looks better against a weaker league average) and a tougher
`lg_pwoba`/`ra9_baseline` lowered pitcher WAR (1.33 → -0.49, same output
looks worse against a stingier league average) — correct direction both
ways — and passing `None` for either reproduces the hardcoded-constant
result exactly (empty-state fallback works).

Market-constants scope (added 2026-08-17): `schema.sql`'s new
`market_baselines` table, `get_market_constants_inputs.sql`, and the
modified `get_player_contract_inputs.sql` all verified the same way —
throwaway MariaDB container, syntax-checked, then after seeding one
`market_baselines` row plus one minimal contract, confirmed
`war_dollar_value`/`recommendation_extend_threshold` actually surface
through both the bulk cohort query and the single-player `LEFT JOIN`.
`contract_value.calculate_surplus_value`/`recommend_contract_action`
exercised directly: doubling `war_dollar_value` roughly doubled
`total_value` (correct — it's a linear multiplier on every year's
value), a higher `recommendation_extend_threshold` flipped a borderline
"Extend" to "Keep short-term" as expected, and `None` for either
reproduces the hardcoded-constant result exactly. Backend test suite:
212 passed, 1 pre-existing unrelated failure (`test_process_player_
success`, confirmed via `git stash` to predate this ticket — a leftover
from ticket 0086's `process_player` change, not touched here) — 4 new
tests total (`compute_league_baselines`'s pooling/fallback,
`compute_market_constants`'s cohort-pooling/fallback), plus
`test_process_single_heap_long` updated for both new calls and the
`get_player_surplus_value_*` tests' shared `_contract_row()` fixture
updated for the two new joined columns. Frontend: `AdminPanel.vue`'s
League Baselines and Market Baselines sections both picked up cleanly
via Vite HMR with no compile errors.

**Bug found and fixed via real `update-db` run (2026-08-17):** the user
ran `init-db` + `update-db` against their real save (`TEST.lg`-equivalent,
66 heaps including 6 long heaps) and hit `unsupported operand type(s) for
*: 'decimal.Decimal' and 'float'` inside `compute_league_baselines`
during the first long heap. Root cause: MariaDB's `SUM()` over an *exact*
numeric column type (the pooled-query's source columns —
`players_career_batting_stats`/`players_career_pitching_stats`'
`pa`/`bb`/`hp`/`h`/`d`/`t`/`hr`/`bf`/`ha`/`hra`/`ra`/`outs` — are all
`SMALLINT`) returns `DECIMAL`, which PyMySQL maps to `decimal.Decimal` —
arithmetic against the plain Python floats `FACTOR_BB`/`FACTOR_1B`/etc.
already are raised `TypeError`. Every `.sql` verification this ticket ran
earlier used a throwaway *empty* schema, so the pooled queries always
returned `NULL` sums and hit the (int-safe) fallback branch instead of
the real arithmetic — the empty-schema check never exercised this path,
which is why it wasn't caught until real data existed. **Fixed:**
`compute_league_baselines` now coerces both pools' `SUM()`-derived fields
to `float` immediately after fetching, before any arithmetic.
`get_market_constants_inputs.sql`/`compute_market_constants` don't
aggregate anything (`players_contract.salaryN` is plain `INT`,
`players_run_value.WAR` is `FLOAT` — both come back as native Python
`int`/`float` from PyMySQL without an intervening `SUM()`), so this class
of bug can't recur there. Verified the fix directly by mocking the pool
fetch functions to return real `decimal.Decimal` values (matching what
PyMySQL actually returns) instead of plain ints/floats — reproduces the
original `TypeError` without the fix, succeeds with it. Strengthened
`test_compute_league_baselines_pools_qualifying_seasons` to use
`Decimal` inputs so this can't silently regress. Full backend suite still
212 passed / 1 pre-existing unrelated failure after the fix.

**Second bug found and fixed via real `update-db` run (2026-08-17):** with
the `Decimal` fix applied, `compute_league_baselines` succeeded
(`Recalibrated league baselines (years 2022-2024): lg_woba=0.3185
lg_pwoba=0.3132 ra9_baseline=2.933` — real numbers, sane range), but
`compute_market_constants` then failed with `(1064, "You have an error in
your SQL syntax ... near 'the years=0/current_year=0 row OOTP writes...'")`
— the exact same failure mode [0055](0055-fix-semicolon-in-comment-breaks-migration-short.md)
already found and fixed once before: `_run_sql_script`'s naive
`sql_script.strip().split(";")` has no notion of `-- ...` comments, so any
semicolon anywhere in the file — including inside one — is treated as a
statement boundary. `get_market_constants_inputs.sql`'s own header
comment read "signed contract (years > 0; the years=0/current_year=0 row
..." — the `;` after "years > 0" split the comment mid-sentence into a
second bogus "statement" that MariaDB correctly rejected. **Fixed:**
replaced that semicolon with a double-dash in the comment (no SQL
semantics changed). Re-scanned every `.sql` file this ticket touches for
the same pattern (`grep -n -- "--.*;"`) — none left. 0055 itself declined
to harden `_run_sql_script`'s splitter against this whole bug class
(explicitly scoped out as a bigger, separate change); this recurrence is
a data point that the fragility is real, but out of scope for this ticket
too — noting it rather than re-deciding it here.

**Full real `update-db` run, end to end (2026-08-17):** with both fixes
applied, the user tore down and redeployed the stack (`podman compose up
-d --build`) and re-ran `update-db` against the real save from scratch
(the earlier failed attempts never reached `mark_heap_processed`, so
`processed_heaps` was empty — a clean, idempotent re-run of all 66 heaps,
not a partial resume). All 6 long heaps + 60 short heaps completed with
zero errors (`processed_heaps` count: 66/66). `league_baselines` gained 6
new rows (one per long heap), values drifting sensibly year over year
(`lg_woba` 0.3185 → 0.3224, `ra9_baseline` 2.933 → 2.625).
`market_baselines` gained 6 new rows: the first long heap correctly fell
back to the hardcoded defaults (0 qualifying contracts existed in the
database yet at that point in the run), every subsequent year found a
real cohort (73–95 players for `war_dollar_value`, 479–605 for
`recommendation_extend_threshold`) and computed real values —
`war_dollar_value` settling in the $5.6M–$7.0M/WAR range (below the old
$8.3M hardcoded default) and `recommendation_extend_threshold`
fluctuating $2.0M–$4.4M/yr (below the old $5M default), consistent with
this save's more diluted economy. Spot-checked both live API endpoints
directly against real players: `get_player_expected_value_percentiles`
for Byron Buxton (rating 1065428) returned `batting_runs_value: -3.925`
at the 66th percentile — the exact shape of the originally-reported
symptom (Kyle Manzardo, -2.9/73rd), now internally consistent under the
recalibrated baseline instead of reading as a bug; `/surplus-value` for
Nolan Schanuel (player 40540) returned `value: 20465317.28`, exactly
`3.43564 WAR × $5,956,770/WAR` (the latest `market_baselines` row) —
confirms the recalibrated constant is live in the request path, not just
computed and stored. No visual/browser check (no browser tool available),
otherwise this ticket's full scope is now verified against real data.
