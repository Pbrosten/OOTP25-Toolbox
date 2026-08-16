# 0068 — Prospect FV/value calculation module

- **Tag:** feat
- **Status:** Closed
- **Depends on:** —
- **Blocks:** [0069](0069-prospect-query-layer-api.md)

## 1. Problem

[0043](0043-prospect-pipeline.md) resolved a full methodology for scoring a
prospect's future value and MLB-promotion readiness, replicating FanGraphs'
Future Value (FV) framework against this app's own ratings data (see 0043's
Design choices for the full derivation and source tables). Nothing in the
codebase computes any of it yet — this ticket is the calculation module
itself, isolated from the query/API layer ([0069](0069-prospect-query-layer-api.md))
and frontend ([0070](0070-prospect-pipeline-frontend.md)) that will consume
it, mirroring how [0056](0056-surplus-value-calculation.md) split the
contract-surplus-value calc out from its own API/frontend sub-tickets.

## 2. Design choices

All resolved in 0043 — this ticket is implementation of that already-agreed
methodology, not a fresh design pass. Restated here at implementation-detail
level:

- **Talent-ceiling projection input construction.** Build the `data` dict
  passed to `BatterProjection`/`PitcherProjection` by taking a player's
  latest `rating_id` and pulling:
  - From `players_batting_talent` / `players_pitching_talent` /
    `players_fielding_position_talent`: the categories that map to the
    projection classes' current-rating inputs (`contact`, `gap`, `eye`,
    `power`, `strikeouts`, `babip` for batters; `stuff`, `control`,
    `pbabip`, `hra`, etc. for pitchers; `pos1`-`pos9` for defensive
    position fitness).
  - From `players_basepath` / `players_fielding` (current, not talent —
    no talent table exists for these): `speed`, `steal`, `baserunning`,
    and the skill-component defense ratings (catcher/infield/outfield
    arm/range/error/etc.).
  - Everything else (`player_id`, `position`, `bats`/`throws`,
    `birth_date`, `prone_overall`) unchanged from the current row.
  - Run the existing class unmodified — no new weighting logic, per
    0043's resolved decision to reuse `BatterProjection`/
    `PitcherProjection` as-is rather than inventing a parallel model.
- **Current-form projection for readiness** uses the same classes with an
  entirely current-ratings `data` dict — i.e., the same construction this
  codebase's other consumers already use (no new input-building code
  needed there, just re-running the existing projection).
- **WAR→FV and FV→value lookup tables** — hardcode as named constants
  (mirroring 0056's `WAR_DOLLAR_VALUE`-style named-constant convention),
  values exactly as agreed in 0043:
  - `HITTER_WAR_TO_FV` / `PITCHER_WAR_TO_FV`: ordered WAR-range → FV grade
    tables (20/30/40/45/50/55/60/70/80), pitcher table applies to SP role
    only.
  - `FV_TO_VALUE`: FV grade → `(surplus_value, expected_war, star_odds)`,
    split by hitter/pitcher, from 0043's table. FV 80 falls back to the FV
    70 row. FV below 35 → `$0` surplus value.
- **RP-role prospects:** `players_pitching.role` (per 0037's `ROLE_MAP`) —
  if RP, return "not available" for FV/value/readiness rather than running
  them through the starter-calibrated table.
- **Missing-input handling:** matches 0056's precedent — no latest rating,
  or a two-way player (per 0028's precedent, not double-counted here
  either) → "not available", not an error.
- **No new table.** Computed at read time from existing rating snapshots,
  same reasoning as 0056 (this is a point-in-time function of the latest
  rating, not something worth persisting per-heap).

## 3. Approach

- New module, `backend/app/player_projection/prospect_value.py` (or
  alongside `contract_value.py` if that's the more natural home — match
  whichever existing module 0056 landed in):
  - `build_talent_projection_input(player_row, batting_talent_row,
    fielding_position_talent_row, basepath_row, fielding_row) -> dict` —
    talent/current hybrid dict construction described above (batter
    variant; analogous pitcher variant).
  - `project_talent_ceiling_war(player) -> float | None` — runs
    `BatterProjection`/`PitcherProjection` against the hybrid input,
    returns annual WAR.
  - `war_to_fv(war: float, player_type: Literal["hitter","pitcher"]) ->
    int` — bucket lookup against `HITTER_WAR_TO_FV`/`PITCHER_WAR_TO_FV`.
  - `fv_to_value(fv: int, player_type) -> dict` — lookup against
    `FV_TO_VALUE`, with the FV80/FV<35 edge-case handling.
  - `calculate_prospect_value(player) -> dict` — orchestrates the above:
    talent-ceiling WAR → FV → surplus value/expected WAR/star odds, plus
    current-form WAR → FV → `mlb_promotion_ready: bool` (current-form FV
    >= 40, only meaningful/returned when the player's team `level != 1`).
- Unit tests against known rating rows (mirroring 0056's test-data
  approach) verifying: talent-ratings substitution only touches the
  correct categories, WAR→FV bucketing at tier boundaries, FV→value
  lookup including the FV80/FV<35 edge cases, RP exclusion, and
  missing-input → "not available".

**Files involved:**
- `backend/app/player_projection/prospect_value.py` (new)
- `backend/tests/player_projection/test_prospect_value.py` (new)

## 4. Post-close correction: RP exclusion removed (user request)

After closing, a real-data review (via 0070) found ~27% of a full org's
pitching prospects (56/210, Philadelphia) coming back "not available" due
to the RP exclusion above — all real relievers, working as designed, but
high enough volume that the user asked to remove the exclusion rather than
keep it. Rationale: `PitcherProjection`'s own role-specific baseline
constants (`ROLE_CONSTANTS` in `pitcher.py` — RP's ~300 PA baseline vs.
SP's ~750, ~0.03 replacement-runs/IP vs. ~0.12) already produce a
meaningfully lower annual WAR for a reliever at equivalent ratings, so
applying the same starters-calibrated `PITCHER_WAR_TO_FV` table to RP
naturally sorts them into lower FV tiers rather than needing a hard
exclusion — verified in code:
`test_calculate_pitcher_prospect_value_rp_produces_lower_war_than_sp_at_same_ratings`.
`calculate_pitcher_prospect_value` no longer special-cases
`players_pitching.role`; every pitcher gets a real FV/value now.
