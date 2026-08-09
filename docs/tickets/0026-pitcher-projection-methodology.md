# 0026 — Pitcher projection methodology + `PitcherProjection` class

- **Tag:** feat
- **Status:** Closed
- **Depends on:** [0025](0025-pitcher-migration-ingestion.md)
- **Blocks:** [0027](0027-pitcher-api-frontend-wiring.md), [0028](0028-pitcher-run-value-war.md)

## 1. Problem

`BatterProjection` (`backend/app/player_projection/batter.py`) turns 20-80
scale ratings into expected counting/rate stats and a wRAA/UBR/Def-runs-based
WAR by looking up each rating in a pre-built rating→outcome table
(`offensive_constants.pkl`, `defensive_constants.pkl`, `injury_constants.pkl`
— loaded once at import time, `backend/app/player_projection/batter.py:9-15`).
No equivalent exists for pitching: no constants table mapping `stuff` /
`movement` / `control` / etc. to K%, BB%, HR%, or any other rate, and no
run-value/WAR formula analogous to `calc_player_values()`.

This was 0015's central "Outstanding" item. The **production** half (rating →
expected PA/AB/H/HR/BB/HBP/K/BA/OBP/wOBA/IP/GS-or-G/RA9/ERA) is no longer
undecided — it's been extracted from
[`docs/resources/OOTP calculator blank.xlsx`](../resources/OOTP%20calculator%20blank.xlsx)'s
"Starting Pitchers"/"Relief Pitchers" tabs and written up in
[wiki/Projections §3](../wiki/Projections.md#3-pitcher-projection-methodology-spreadsheet-only--not-yet-implemented),
the same source `BatterProjection`'s methodology came from. The **value/WAR**
half was explicitly out of scope for that extraction and is still an open
design question here.

## 2. Design choices

- **Output stats — resolved.** `players_pitching_expected` gets `PA, AB, H,
  HR, BB, HBP, K, BA, OBP, wOBA, IP, GS (SP) / G (RP), RA/9, ERA` — the exact
  set the spreadsheet's "Projected Production" block computes. See
  [wiki/Projections §3.6](../wiki/Projections.md#36-whats-confirmed-vs-still-open)
  for the full confirmed/open breakdown; this supersedes the "what output
  stats?" question previously listed here.
- **Role handling (SP vs. RP) — resolved against real dump data.**
  `staging.players_pitching.role` is a numeric roster-role code (also used
  in `staging.players_roster_status`), and — contrary to 0024's original
  read of a smaller sample — the table has one row for **every player in
  the league** (~135k rows/heap in `TEST.lg`, matching `staging.players`'
  row count almost exactly), not just pitching-capable ones; non-pitchers
  get `role = 0`. Cross-referencing `role` against actual `GS`/`G` usage in
  `staging.players_career_pitching_stats` confirmed: `role = 11` → Starting
  Pitcher (sampled players: 31/31 and 27/27 starts), `role = 12` → Relief
  Pitcher (sampled: 35 G, 0 GS), `role = 13` → Closer, a small subset with
  all-relief usage (sampled: 58 G, 0 GS). Since the spreadsheet only defines
  two curves, role 13 is folded into the RP bucket (`PitcherProjection.ROLE_MAP`).
  Non-pitcher rows (`role = 0`) are filtered out at **both** layers: a
  `WHERE s.role IN (11, 12, 13)` added to `migration_short.sql`'s
  `players_pitching`/`players_pitching_talent` INSERTs (amending
  [0025](0025-pitcher-migration-ingestion.md), already closed, since that's
  where the population question actually lives), and defensively in
  `PitcherProjection.__init__` (raises on any other role value, caught by
  `process_pitcher()` the same way any other bad-input exception is).
  `players_pitching` also needed a new `role` column (0024's schema didn't
  store it) so `PitcherProjection` can pick SP vs. RP back up at fetch time
  without re-joining staging (which is wiped every heap).
- **The "Playing Time" input gap — resolved: default to 1.0 for v1.** No
  source exists in the OOTP export for the spreadsheet's manual per-player
  rotation/bullpen-share input (wiki §3.4). Rather than build a derived-share
  heuristic now, every pitcher gets a full share — this overstates playing
  time for organizational depth/fringe arms and is a known limitation, not a
  per-player value; `PLAYING_TIME_INPUT` in `pitcher.py` is the one constant
  to revisit if this needs refining later.
- **Age-development (wiki §3.2) — skipped, current ratings only.**
  `BatterProjection` doesn't implement the spreadsheet's age-blend at all
  today (it uses current ratings directly), and the pitcher export is
  missing one of the three makeup traits the blend needs (`players.mysql`
  has `personality_work_ethic`/`personality_intelligence` as raw integers,
  but no Adaptability field at all, and none are pre-bucketed to the
  spreadsheet's H/N/L categories). `PitcherProjection` matches
  `BatterProjection`'s actual (simpler) behavior for consistency, rather
  than being more spreadsheet-faithful than the batter side already is.
  `players_pitching_talent`'s potential ratings aren't consumed by 0026 as a
  result — nothing here removes that table, in case a future ticket revisits
  age-development for both player types together.
- **Question: run-value/WAR formula and how it combines with batting WAR for
  two-way players.** Deferred from [0024](0024-pitcher-schema-ratings-tables.md)
  to here. The spreadsheet does have a full Value/WAR formula (dynamic
  runs/win, hold-based baserunning runs, a zeroed-out defense-runs
  placeholder — see the "Current Value"/"Projected Value" columns), but it
  was deliberately excluded from the wiki extraction pass, so treat it as
  unverified until someone does the same cell-by-cell read-through for it
  that §3 did for Production. **Not decided.**
- **vsL/vsR splits and per-pitch-type grades.** Confirmed **not needed** —
  the spreadsheet's production methodology only reads the `overall` rating
  block (wiki §3.1), matching 0024's decision to leave these columns out of
  the schema.

## 3. Approach

- `pitching_constants.pkl`: one DataFrame (indexed by rating 0/20-95, same
  shape as `offensive_constants.pkl`) with `SP_*`/`RP_*` columns for the four
  rating→rate curves (K, HR, non-HR-hit, BB) plus each role's
  stamina→TBF-per-appearance curve — read directly from
  `docs/resources/OOTP calculator blank.xlsx`'s "Projection Constants" sheet
  via `openpyxl` (columns W-AA for SP, AC-AG for RP), not retyped from the
  wiki's illustrative cell references. Durability (prone→multiplier) reuses
  the *existing* `injury_constants.pkl`, which already has `Starter`/
  `Reliever` columns nobody was reading yet — no new pickle needed there.
- `backend/app/player_projection/pitcher.py::PitcherProjection`: baseline
  (fixed AB=900/300) → actual-playing-time scaling → rates, per wiki §3.3-3.5,
  role-dispatched via `self.role` ('SP'/'RP') set from `ROLE_MAP` in
  `__init__`. **Verified formula-for-formula against the source workbook**:
  fed the spreadsheet's own pre-filled SP and RP example rows (Stuff 55/
  Control 70/pBABIP 50/HRR 55/Stam 65/Normal prone for SP; Stuff 75/Control
  45/pBABIP 50/HRR 60/Stam 30/Normal prone for RP) through both
  `PitcherProjection` and the live workbook (`openpyxl`, `data_only=True`)
  and diffed every output stat — exact match (to float noise) on
  PA/AB/H/HR/BB/HBP/K/BA/OBP/wOBA/IP/GS-or-G/RA9/ERA for both roles.
  Value/WAR output is blocked on [0028](0028-pitcher-run-value-war.md) —
  production doesn't need to wait for it.
- `players_pitching_expected` added to `schema.sql` with the column set from
  §2 above, FK'd to `players_pitching(rating_id)` (same pattern as
  `players_batting_expected` → `players_batting`). `players_pitching` also
  gained a `role SMALLINT` column (see Design choices).
- `migration_short.sql`: both `players_pitching`/`players_pitching_talent`
  INSERTs now select `s.role` and filter `WHERE ... AND s.role IN (11, 12, 13)`
  — amends [0025](0025-pitcher-migration-ingestion.md)'s already-closed SQL,
  since the "staging.players_pitching has non-pitcher rows" discovery
  happened here, not there.
- New `get_pitcher_projection_inputs.sql` (mirrors `get_projection_inputs.sql`),
  and `fetch_pitcher_projection_inputs()` / `project_pitchers()` /
  `insert_pitcher_projections()` in `update.py`, `process_pitcher()` /
  `update_pitching_projection_batches()` / `pitching_proj_scripts` in
  `projection.py` — parallel to the batter path throughout, wired into
  `process_single_heap()` right after the batter pass; `projections_inserted`
  in the returned counts sums both.
- Verified end-to-end against a live MariaDB using an isolated throwaway
  database (not the shared dev `ootp` database, which had real in-progress
  data from an actual save) — real `fetch → project → insert` run through
  the actual Flask app/DB code path, confirmed rows land in
  `players_pitching_expected` matching the workbook-verified values exactly.

**Files involved:**
- `backend/app/player_projection/pitcher.py` (new)
- `backend/app/player_projection/constants/pitching_constants.pkl` (new)
- `backend/app/player_projection/__init__.py` (modified — export `PitcherProjection`)
- `backend/app/db/sql_scripts/schema.sql` (modified — `players_pitching.role`,
  `players_pitching_expected`)
- `backend/app/db/sql_scripts/migration/migration_short.sql` (modified —
  amends 0025's INSERTs with `role` + population filter)
- `backend/app/db/sql_scripts/migration/get_pitcher_projection_inputs.sql` (new)
- `backend/app/db/update.py`, `backend/app/db/projection.py` (modified)
- `backend/tests/db/test_update.py` (modified — pitcher mocks added to
  `test_process_single_heap_short`)
