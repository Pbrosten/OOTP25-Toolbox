# 0028 — Pitcher run-value/WAR: methodology, schema, and projection wiring

- **Tag:** feat
- **Status:** Closed
- **Depends on:** [0026](0026-pitcher-projection-methodology.md)
- **Blocks:** [0027](0027-pitcher-api-frontend-wiring.md)

## 1. Problem

[0026](0026-pitcher-projection-methodology.md) implements pitcher *production*
(expected PA/AB/H/.../RA9/ERA) but explicitly punts the *value* half: no
run-value/WAR formula for pitchers, and no table to store it in. This was
originally raised in [0024](0024-pitcher-schema-ratings-tables.md)'s Design
choices, deferred to 0026, and deferred again there — it's never actually
been resolved, just passed down the chain. `PitcherProjection` has no
`calc_player_values()` analogous to `BatterProjection.calc_player_values()`
(`backend/app/player_projection/batter.py:224-241`), and 0027's frontend
wiring can't show a pitcher value percentile card without something to query
(`BatterPercentiles`'s equivalent view reads `players_run_value` via
`get_player_expected_value_percentiles.sql`).

## 2. Design choices

- **Extend `players_run_value` or add a parallel table?** Deferred here from
  0024/0026. Checked the existing query this feeds
  (`backend/app/db/sql_scripts/api/get_player_expected_value_percentiles.sql:14`):
  its comparison population is filtered with `p.position != 'P'` — the
  current table and its one consumer already assume "batting value only,
  pitchers excluded," not just by convention but by an explicit filter.
  Extending it with pitching columns would mean either dropping that filter
  (and deciding how a two-way player's single `total_runs`/`WAR` row nets
  batting and pitching value — unresolved, see below) or keeping the filter
  and shipping dead columns for the 99% of rows that are pure batters.
  **Chosen:** add a parallel `players_pitching_run_value` table, keyed
  1:1 on `rating_id` like `players_run_value`. Matches the parallel-table
  precedent already set by `players_pitching`/`players_pitching_expected`
  (0024/0026) and keeps the existing batting query untouched.
- **Two-way players.** With a parallel table, a two-way player's rating_id
  can have rows in both `players_run_value` and `players_pitching_run_value`
  with independent `WAR` columns. **Chosen: don't net them** — no combined
  "total player WAR" column or query in this ticket. The percentiles UI
  (0027) shows batting and pitching value separately (`BatterPercentiles` /
  `PitcherPercentiles` are already separate components per 0015's Approach),
  so there's no existing consumer that needs a netted figure. Revisit only
  if a future ticket asks for one.
- **WAR formula source — done.** Full cell-by-cell read-through of the
  Value block (`'Starting Pitchers'!DB:DH` / `'Relief Pitchers'!DC:DI`)
  performed via `openpyxl`, written up as
  [wiki/Projections.md §3.7](../wiki/Projections.md#37-pitcher-valuewar-methodology-implemented-0028).
  Two real findings, both surfaced to the user and resolved before
  implementation:
  - **Reliever leverage WAR adjustment.** The workbook multiplies RP-only
    WAR by an `XLOOKUP` against a "Leverage" rating (High/Medium/Low →
    1.5/1.0/0.75), but that input is a hardcoded manual literal in the
    template (`='Medium'`), not a formula reading real data — same shape as
    0026's Playing Time gap. **Decision: omit the multiplier entirely**
    (not default it to a no-op 1.0) — SP and RP `WAR` use the identical
    `total_runs / runs_per_win` formula.
  - **Defense runs — confirmed always zero.** Verified directly against
    `'Projection Constants'!V7:V23`/`V4`: the pitcher defense-runs curve is
    literally `0` at every rating step. There's also no pitcher fielding
    rating in the OOTP export (0024 already excluded fielding from
    `players_pitching`). **Decision: no `defense_runs` column at all** in
    `players_pitching_run_value` — the term is inert in the source
    spreadsheet itself, not merely unavailable to this pipeline.
- **`runs_prevented` is already derived — reused.** `PitcherProjection.calc_rates()`
  (0026) now stashes it as `self.runs_prevented` (was a local); `calc_player_values()`
  reads that attribute directly as `pitching_runs` rather than recomputing.
- **Resolved:** `players_pitching_run_value` column set —
  `rating_id, pitching_runs, baserunning_runs, total_runs, WAR`. No
  `replacement_runs` column, matching `players_run_value`'s own precedent
  (`BatterProjection` computes `Replace_runs` but it's folded into
  `total_runs` without its own column — `batter.py:236`). No `defense_runs`
  column, per the finding above. `baserunning_runs` needed one new input:
  `hold` (already a `players_pitching` column from 0024, unused until now)
  — added to `get_pitcher_projection_inputs.sql`, and the Hold→runs/IP curve
  (shared by SP and RP, not role-prefixed) added to `pitching_constants.pkl`
  as a `BR` column.

## 3. Approach

- `docs/wiki/Projections.md` §3.7 (new): cell-by-cell read-through of the
  Value block, same rigor as §3.3-3.5, covering both findings above.
- `players_pitching_run_value` added to `schema.sql`: `rating_id INT PRIMARY
  KEY` FK'd to `players_rating` (matching `players_run_value`'s own FK
  target, not `players_pitching`'s), plus `pitching_runs, baserunning_runs,
  total_runs, WAR` — no `batting_runs`/`fielding_runs` (don't apply), no
  `defense_runs` (confirmed always zero in the source spreadsheet), no
  `replacement_runs` (folded into `total_runs`, matching `players_run_value`'s
  own precedent of not storing it separately). `DROP TABLE IF EXISTS
  players_pitching_run_value;` added ordered with `players_run_value`'s drop.
- `PitcherProjection.calc_player_values()` added
  (`backend/app/player_projection/pitcher.py`): reuses `self.runs_prevented`
  (promoted from a `calc_rates()` local to an instance attribute) for
  `pitching_runs`; new `lookup_baserunning()` method for the
  role-independent Hold→runs/IP curve; `calc_expected_stats()` now returns
  a `"pitching_value"` key alongside `"pitching"`.
- `pitching_constants.pkl`: added an unprefixed `BR` column (Hold→runs/IP,
  shared by SP/RP) extracted the same way §3.3's curves were — via
  `openpyxl` against `'Projection Constants'!$AB$7:$AB$23`.
- `get_pitcher_projection_inputs.sql`: added `pp.hold` to the SELECT
  (column already existed on `players_pitching` since 0024, just unused).
- `backend/app/db/projection.py`: added a `"pitching_value"` entry to
  `pitching_proj_scripts` with the `INSERT IGNORE INTO
  players_pitching_run_value` statement.
- `backend/app/db/update.py`: `insert_pitcher_projections()`'s `batches`
  dict now includes `"pitching_value"` alongside `"pitching"`.
- Left the API/frontend percentile wiring to 0027 — this ticket only gets
  the table populated.

**Files involved:**
- `docs/wiki/Projections.md` (modified — new §3.7 Value/WAR section)
- `backend/app/db/sql_scripts/schema.sql` (modified)
- `backend/app/player_projection/pitcher.py` (modified)
- `backend/app/player_projection/constants/pitching_constants.pkl` (modified — new `BR` column)
- `backend/app/db/sql_scripts/migration/get_pitcher_projection_inputs.sql` (modified — added `pp.hold`)
- `backend/app/db/projection.py`, `backend/app/db/update.py` (modified)
- `backend/app/db/projection.py` (modified)
