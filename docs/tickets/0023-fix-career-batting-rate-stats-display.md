# 0023 — Fix OBP/SLG/OPS in the career batting stats table

- **Tag:** fix
- **Status:** Closed
- **Depends on:** —
- **Blocks:** —

## 1. Problem

`frontend/src/components/PlayerDetails.vue`'s career batting stats table
shows wrong OBP/SLG/OPS values while counting stats (PA, AB, R, H, HR, SB)
display correctly. Two distinct bugs, both in the frontend:

- **Display formatting breaks for any rate stat ≥ 1.000.** Every rate cell
  is rendered as `` .{{ value.toFixed(3).split('.')[1] }} `` to strip the
  leading `0` OOTP-style (e.g. `0.298` → `.298`). AVG/OBP/SLG are almost
  always `< 1`, so this looks fine for them — but OPS (their sum) routinely
  isn't: `1.023.toFixed(3)` → `"1.023"` → `.split('.')[1]` → `"023"` →
  rendered as `.023`, silently dropping the leading digit. Affected lines:
  151, 155, 160, 166, 179, 183, 193, 197, 201, 205, 216, 220, 224, 228.
- **OBP formula is missing sacrifice flies.** Both the per-row and totals
  calculations (lines 65, 155, 165–166) compute OBP as
  `(H + BB + HBP) / PA` instead of the textbook
  `(H + BB + HBP) / (AB + BB + HBP + SF)`. `get_player_career_batting_mlb.sql`
  / `get_player_career_batting_milb.sql` don't even `SELECT` `sf` (or `sh`)
  from `players_career_batting_stats`, even though that table has both
  columns (populated by `migration_long.sql`) — there's currently no way to
  compute the correct formula without adding them to the query. This
  understates OBP (and therefore OPS) for any player with sac flies.
- **Row-level SLG/OPS can divide by zero.** The per-row OPS cell (line
  164–168) guards only on `stat.pa > 0`, but its SLG term divides by
  `stat.ab`, which can be `0` while `pa > 0` (e.g. a stint that's entirely
  walks/HBP) — producing a `NaN` cell despite the guard.

No `obp`/`slg`/`ops` columns exist anywhere in the schema today — only
counting stats are stored (`players_career_batting_stats`, `schema.sql:66-103`),
and rates are computed client-side from the API's counting-stat response.
That part already matches "ingest counting stats, compute rates
separately"; this ticket is about fixing the computation/display, not about
where it happens.

## 2. Design choices

- **Where the fix lives.** Options considered: (a) fix in the frontend only
  — correct the formatting bug and the OBP formula in `PlayerDetails.vue`,
  no schema/API changes; (b) move rate-stat computation to the backend
  (ingestion time or query time), matching how `players_batting_expected`'s
  projected AVG/OBP/SLG are already computed server-side in
  `app/player_projection/batter.py`. **Chosen: (a)** — the bug is in the
  display/formula layer, not in what's stored; moving computation
  server-side is a real architectural improvement (single source of truth,
  no duplicated baseball-stat math in TS) but is a separate, larger change
  than what's needed to fix this specific defect. Flagged here as a
  reasonable follow-up, not required by this ticket.
- **Formatting fix.** Stop stripping the leading digit via string
  manipulation. Use a small formatter that renders `< 1` values as `.XXX`
  (OOTP convention) and `>= 1` values as `X.XXX` (standard OPS notation) —
  e.g. `value.toFixed(3).replace(/^0\./, '.')`, which only strips a leading
  `"0."`, not any leading digit.
- **OBP formula.** Add `sf` (and `sh`, needed to reconstruct `AB + BB + HBP
  + SF` correctly per OOTP's PA accounting) to both career-batting SQL
  queries, and switch the OBP calculation to the standard formula.
  **Outstanding:** confirm OOTP's `pa` field's exact composition (does it
  include `sh`?) against a real dump before assuming `ab + bb + hp + sf` is
  the correct denominator — if `pa` already excludes `sh`, the simpler
  `(h+bb+hp)/(ab+bb+hp+sf)` holds; if not, adjust. Not verifiable from the
  code alone.

## 3. Approach

- `backend/app/db/sql_scripts/api/get_player_career_batting_mlb.sql` and
  `get_player_career_batting_milb.sql`: add `SUM(cb.sf) AS sf` (and `sh` if
  needed per the outstanding question above) to the `SELECT`/`GROUP BY`.
- `frontend/src/components/PlayerDetails.vue`:
  - Add a `formatRate(value: number | null): string` helper implementing
    the `< 1` / `>= 1` formatting split described above; use it in place of
    every `` .{{ x.toFixed(3).split('.')[1] }} `` occurrence (14 call sites).
  - Update the OBP formula (both per-row, lines 155/165-166, and in
    `totals`, line 65) to `(h + bb + hp) / (ab + bb + hp + sf)`, guarding
    the new denominator against `0` the same way `pa > 0` is guarded today.
  - Fix the per-row SLG/OPS cells (lines 158-168) to guard on `stat.ab > 0`
    for the SLG term specifically, not just `stat.pa > 0`, so a walks-only
    stint renders `-` for SLG/OPS instead of `NaN`.
- Manually verify against a player with real sac-fly and OPS ≥ 1.000
  seasons (spot-check in the running app) rather than relying on unit tests
  alone, since this is a display-layer bug that unit tests wouldn't have
  caught the first time either.

**Files involved:**
- `frontend/src/components/PlayerDetails.vue` (modified)
- `backend/app/db/sql_scripts/api/get_player_career_batting_mlb.sql` (modified)
- `backend/app/db/sql_scripts/api/get_player_career_batting_milb.sql` (modified)
