# 0028 — Pitcher run-value/WAR: methodology, schema, and projection wiring

- **Tag:** feat
- **Status:** Open
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
- **WAR formula source.** The source spreadsheet
  (`docs/resources/OOTP calculator blank.xlsx`, "Starting Pitchers"/"Relief
  Pitchers" tabs) has a full Value/WAR block per 0026's Design choices
  (dynamic runs/win, hold-based baserunning runs allowed, a zeroed-out
  defense-runs placeholder) but it was deliberately excluded from the
  [wiki/Projections.md §3](../wiki/Projections.md#3-pitcher-projection-methodology-spreadsheet-only--not-yet-implemented)
  extraction pass, which only covers Production. **Not yet done:** this
  ticket needs the same cell-by-cell read-through §3 did for production,
  written up as a new wiki section, before implementation — don't
  reverse-engineer the formula from code, follow the established
  spreadsheet-extraction process this project already uses for batter/pitcher
  production.
- **`runs_prevented` is already derived.** Wiki §3.5 notes pitcher
  `RA/9`/`ERA` needs a wRAA-style `runs_prevented` intermediate
  (`(0.327 - wOBA_against) / 1.2 * PA`) and that 0026 already computes it as
  part of production, even though it's nominally a Value-section formula.
  This ticket's `calc_player_values()`-equivalent should reuse that existing
  value rather than recomputing it — check what 0026 actually landed on
  (an attribute on the `PitcherProjection` instance vs. a local in
  `calc_expected_stats()`) once it's implemented.
- **Outstanding:** exact `players_pitching_run_value` column set — depends
  entirely on which spreadsheet Value columns the read-through above
  confirms are in scope (e.g. is a "replacement runs" term included the way
  `BatterProjection` has one? `batter.py:236`).

## 3. Approach

- Extend `docs/wiki/Projections.md` with a new "§X Pitcher value/WAR
  methodology" section, same rigor as §3 (cell references, confirmed vs.
  open breakdown), covering the spreadsheet's Value/WAR block.
- Add `players_pitching_run_value` to `schema.sql`, shaped like
  `players_run_value` (`rating_id INT PRIMARY KEY`, FK to
  `players_rating`, plus whatever run-component columns the wiki
  read-through confirms) — no `batting_runs`/`fielding_runs` columns, since
  those don't apply to pitchers.
- Add a `DROP TABLE IF EXISTS players_pitching_run_value;` line to
  `schema.sql`'s drop block, ordered with the other pitching tables.
- Add `calc_player_values()` to `PitcherProjection`
  (`backend/app/player_projection/pitcher.py`, from 0026), returning a
  `value` dict the same shape `BatterProjection.calc_player_values()`
  produces, folded into `calc_expected_stats()`'s output.
- `backend/app/db/projection.py`: add a `"pitching_value"` (or similarly
  named) entry to `proj_scripts` with the `INSERT IGNORE INTO
  players_pitching_run_value` statement, and wire it into whatever
  pitcher-side batching 0026 added to
  `update_projection_batches`/`process_player`.
- Leave the API/frontend percentile wiring to 0027 — this ticket only needs
  to get the table populated; 0027 already plans to read "the pitching
  run-value table" (now: this ticket's table, not 0026's) from
  `players_pitching_run_value`.

**Files involved:**
- `docs/wiki/Projections.md` (modified — new Value/WAR section)
- `backend/app/db/sql_scripts/schema.sql` (modified)
- `backend/app/player_projection/pitcher.py` (modified)
- `backend/app/db/projection.py` (modified)
