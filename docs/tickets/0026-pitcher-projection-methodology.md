# 0026 — Pitcher projection methodology + `PitcherProjection` class

- **Tag:** feat
- **Status:** Open
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
- **Role handling (SP vs. RP) — mechanism resolved, classification open.**
  The spreadsheet uses genuinely different rate-lookup curves and baseline
  workload constants per role (wiki §3.3), not just a scaling factor — so
  `PitcherProjection` needs two constant tables, not one. **Still open:**
  how `staging.players_pitching.role`/`position` maps to "use the SP table"
  vs. "use the RP table" hasn't been checked against real dump data.
- **The "Playing Time" input gap — newly discovered, unresolved.** The
  spreadsheet's playing-time scaling (wiki §3.4) depends on a manual
  per-player share (0-1ish) that has no source in the OOTP ratings export —
  unlike batters, whose workload is fully derived from position + the
  `Prone` durability rating. Options: default everyone to a full share
  (loses the rotation-depth signal the spreadsheet author was manually
  encoding), derive a share from `role`/roster-order fields already in
  `staging.players_pitching`/`staging.players_roster_status`, or add a
  manual override field. **Not decided** — needs to be before implementation,
  since it directly scales every counting stat.
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

- Build `backend/app/player_projection/constants/pitching_constants.pkl` (or
  two tables, SP/RP) encoding the rating→rate lookup curves in
  [wiki/Projections §3.3](../wiki/Projections.md#33-baseline-production) —
  the pitching equivalent of `offensive_constants.pkl`, loaded once at
  import time the same way (`backend/app/player_projection/batter.py:9-15`).
- Add `backend/app/player_projection/pitcher.py::PitcherProjection`, shaped
  like `BatterProjection`: `__init__(data: dict)` pulling ratings out of a
  `players_pitching`/`players_pitching_talent` row, implementing the
  baseline → playing-time-scaling → rates pipeline from wiki §3.3-3.5, and a
  `calc_expected_stats()` entry point returning a dict consumed by
  `update.py`/`projection.py`. Value/WAR output is blocked on the still-open
  question above — production doesn't need to wait for it.
- Add `players_pitching_expected` to `schema.sql` with the column set from
  §2 above. A pitching run-value table is still blocked on the Value/WAR
  design question — that follow-up is [0028](0028-pitcher-run-value-war.md),
  filed once this ticket's production scope was resolved, rather than
  guessing its shape now.
- Wire into `app/db/update.py::process_single_heap()` /
  `app/db/projection.py::project_players()` alongside the existing batter
  pass — same per-heap trigger, parallel code path, not a shared one (batters
  and pitchers have different input shapes).

**Files involved:**
- `backend/app/player_projection/pitcher.py` (new)
- `backend/app/player_projection/constants/` (new pickle(s))
- `backend/app/db/sql_scripts/schema.sql` (modified — expected/run-value
  tables)
- `backend/app/db/update.py`, `backend/app/db/projection.py` (modified)
