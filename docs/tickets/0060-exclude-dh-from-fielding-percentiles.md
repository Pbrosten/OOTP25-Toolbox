# 0060 — Exclude DH players from fielding percentiles

- **Tag:** fix
- **Status:** Closed
- **Depends on:** —
- **Blocks:** —

## 1. Problem

DH players' pages show fielding-related percentile bars even though a DH
never fields. Reported directly: DH fielding percentiles should not be
shown — they add noise/bloat to a section that isn't meaningful for that
position.

Root cause traced to two independent leaks in `BatterPercentiles.vue`'s two
backend queries, both stemming from the same gap: nothing in the pipeline
treats `DH` as "doesn't field," even though `players.position` stores it as
the literal string `'DH'` (`VARCHAR(2)`, `schema.sql:62`) alongside real
fielding positions.

- **Leak #1 (confirmed live, actually renders a bar today).**
  `get_player_expected_value_percentiles.sql`'s `expected_filtered` cohort
  only excludes pitchers (`WHERE p.position != 'P' ...`), so DH is pooled
  with catchers/infielders/outfielders when computing
  `fielding_runs_percentile`, and the query computes that percentile for the
  target row unconditionally regardless of the target's own position.
  `BatterPercentiles.vue`'s "Value" section renders `fielding_runs_percentile`
  (`valueOrder`, labeled "Fielding Run Value") gated only on
  `isMlb && xStatsBat`, no position check. Live proof: Shohei Ohtani
  (player_id 33695, DH, rating_id 1065504) —
  `GET /api/players/ratings/1065504/expected/value/percentiles` returns
  `fielding_runs_percentile: "0"`, `fielding_runs_value: -15.1667`, and this
  bar renders on his page today.
- **Leak #2 (latent — dead chrome today, one edit from a real bug).**
  `get_player_expected_fielding_percentiles.sql` classifies `position = 'DH'`
  into `position_group = 'dh'` and computes `fielding_value`/
  `fielding_value_percentile` from `players_fielding_expected.DH` — a
  placeholder column OOTP exports even though it isn't a real fielding
  grade — percentiled against other DH players' same placeholder column, a
  comparison that's meaningless since DH doesn't field. In
  `BatterPercentiles.vue`, `positionGroupFields` only defines
  `catcher`/`infield`/`outfield`; `filteredFieldingPercentiles` falls back
  for any unrecognized group to "every key ending in `_percentile` with a
  valid value," which for `dh` is just `fielding_value_percentile`. The
  "Fielding" section itself is gated on `isMlb && filteredFieldingPercentiles`
  — a plain object is always truthy in JS, so this is effectively just
  `isMlb`, and today it renders empty section chrome (icon, Poor/Average/
  Great labels, zero bars) for every DH, because `fieldOrder` (the list that
  actually picks which keys render) happens to omit
  `fielding_value_percentile`. That omission is incidental, not a
  deliberate DH exclusion — one `fieldOrder` edit away from surfacing the
  same nonsensical DH fielding-value percentile as a real bar.

## 2. Design choices

- **Fix at the SQL layer, not just the frontend — mirrors ticket
  [0037](0037-split-sp-rp-percentile-cohorts.md)'s precedent** (SP/RP cohort
  pollution, fixed by scoping each cohort CTE, no response-shape change).
  **Chosen:** exclude DH from both fielding-adjacent cohorts and null out
  the target's own fielding fields when the target is DH, so the API stops
  returning numbers that shouldn't exist rather than relying on the frontend
  to hide them.
- **Also fix the frontend, not SQL-only.** Leak #2 is currently masked only
  by `fieldOrder`'s incidental omission, and the "Fielding" section's
  always-truthy `v-if` renders empty chrome for DH regardless of backend
  changes. **Chosen:** gate both the Value section's fielding bar and the
  whole Fielding section on position/position_group, so the frontend
  degrades correctly on its own and doesn't silently regress if `fieldOrder`
  is ever touched again.
- **Outstanding:** none — this mirrors 0037's established pattern closely
  enough that no new design question came up.

## 3. Approach

- `backend/app/db/sql_scripts/api/get_player_expected_value_percentiles.sql`:
  - `expected_filtered`: change `p.position != 'P'` to
    `p.position NOT IN ('P', 'DH')` so DH is excluded from the comparison
    pool the same way pitchers already are.
  - `target_player`: join `players` to read the target's own `position`
    (currently only reads `players_rating`).
  - Wrap the `fielding_runs_percentile`/`fielding_runs_value` SELECT
    expressions so they return `NULL` when the target's own position is
    `'DH'` (e.g. `CASE WHEN t.position = 'DH' THEN NULL ELSE ... END`),
    since a DH has no real fielding-run value to report even before cohort
    pooling comes into it.
- `backend/app/db/sql_scripts/api/get_player_expected_fielding_percentiles.sql`:
  - Return `fielding_value`/`fielding_value_percentile` as `NULL` when
    `position_group = 'dh'`, rather than computing them from the
    placeholder `players_fielding_expected.DH` column.
- `frontend/src/components/percentiles/BatterPercentiles.vue`:
  - Value section: skip `fielding_runs_percentile` from the rendered
    `valueOrder` list when the target's position/position_group is `dh`
    (mirrors how catcher/infield/outfield fields are already selected by
    group).
  - Fielding section: change the section's `v-if` from the always-truthy
    `filteredFieldingPercentiles` object check to something that reflects
    whether there are actual bars to show (e.g.
    `Object.keys(filteredFieldingPercentiles).length > 0`), so DH — and any
    future position with no real bars — doesn't render empty section chrome.
- Verify against the real `TEST.lg` save on the live dev DB (established
  pattern): confirm a known DH player (Ohtani, 33695) no longer returns
  `fielding_runs_percentile`/`fielding_value_percentile` from either
  endpoint, that a real fielder (catcher/infield/outfield) is unaffected,
  and that the DH's page no longer renders the Fielding Run Value bar or
  empty Fielding section chrome.

**Files involved:**
- `backend/app/db/sql_scripts/api/get_player_expected_value_percentiles.sql` (modified)
- `backend/app/db/sql_scripts/api/get_player_expected_fielding_percentiles.sql` (modified)
- `frontend/src/components/percentiles/BatterPercentiles.vue` (modified)

**Implementation note:** `filteredFieldingPercentiles`'s original fallback
branch already relied on `isValidPercentile` to drop invalid keys — the
actual bug there was that `isValidPercentile` coerced `null` via
`Number(null) === 0`, a *valid* percentile, so a nulled-out
`fielding_value_percentile` would still render a bogus 0th-percentile bar.
Fixed `isValidPercentile` to explicitly reject `null`/`undefined` rather
than adding a separate DH-specific frontend check — this is the general
fix and also cleans up the Value section's `fielding_runs_percentile` bar
for DH with no position-specific branching needed there either. Combined
with nulling both fields at the SQL layer, `filteredFieldingPercentiles`
now naturally evaluates to `{}` for DH, so gating the Fielding section on
`Object.keys(filteredFieldingPercentiles).length > 0` (replacing the
always-truthy plain-object check) hides the section entirely.

**Verified** against the real `TEST.lg` save on the live dev DB
(established pattern; required a backend container restart to pick up the
SQL changes — the dev container doesn't run Flask in debug/reload mode):
- Both SQL files run directly against `mariadb`: for Ohtani (rating_id
  1065504, DH), `get_player_expected_value_percentiles.sql` now returns
  `fielding_runs_percentile`/`fielding_runs_value` as `NULL` (previously
  `"0"`/`-15.1667`); `get_player_expected_fielding_percentiles.sql` returns
  `fielding_value`/`fielding_value_percentile` as `NULL`. A real fielder
  (rating_id 1075212, 1B) is unaffected on both endpoints
  (`fielding_runs_percentile: "0"`, `fielding_value_percentile: "22"`,
  `infield_arm_percentile`/`infield_range_percentile` populated).
- Re-verified the same over HTTP after a backend restart: `GET
  /api/players/ratings/1065504/expected/value/percentiles` and
  `.../expected/fielding/percentiles` both return `null` for every
  fielding-related key for Ohtani; the same routes for player 1075212 (1B)
  return real values, unchanged.
- Frontend: Vite HMR picked up the `BatterPercentiles.vue` change with no
  compile errors. `npx vue-tsc -b` reports the same 32 pre-existing type
  errors with and without this change (confirmed via `git stash`) — none
  attributable to this ticket's edits, a pre-existing broken type-check
  environment unrelated to this fix.
- Backend suite: 118 passed (no Python code touched by this ticket).
