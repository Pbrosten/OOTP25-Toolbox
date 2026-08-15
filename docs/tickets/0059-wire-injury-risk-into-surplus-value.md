# 0059 — Wire injury risk into the surplus-value calculation

- **Tag:** feat
- **Status:** Closed
- **Depends on:** [0056](0056-surplus-value-calculation.md)
- **Blocks:** —

## 1. Problem

[0041](0041-trade-target-finder.md)/[0042](0042-contract-arbitration-analyzer.md)
both chose `players.prone_overall` as the injury-risk proxy, but 0056 never
actually used it — `calculate_surplus_value` has no injury discount at all.
A durability-fragile player currently gets the exact same multi-year
projection as an iron-man with identical WAR, which understates risk for
exactly the players (aging or fragile veterans on long deals) this tool
most needs to flag.

## 2. Design choices

- **Reuse the existing category bucketing and multipliers — don't invent
  new ones.** `BatterProjection`/`PitcherProjection` (`batter.py:53-58`,
  `pitcher.py:64-69`) already bucket `prone_overall` into
  Durable (<25) / Normal (<125) / Fragile (<175) / Wrecked (>=175), and
  already look up a real per-season availability multiplier for that
  bucket from `injury_constants.pkl`:

  | | Batter | Starter | Reliever |
  |---|---|---|---|
  | Durable | 1.02 | 1.10 | 1.03 |
  | Normal | 1.00 | 1.00 | 1.00 |
  | Fragile | 0.99 | 0.89 | 0.98 |
  | Wrecked | 0.95 | 0.76 | 0.86 |

  (a 5th "Iron Man" row exists in the pickle but is unreachable by the
  existing bucketing logic in both projection classes — pre-existing,
  out of scope here.) **Chosen:** reuse these exact numbers as plain
  constants in `contract_value.py`, not a fresh derivation — they're
  already the project's real answer to "how much does this durability
  category affect a season's value," just not yet applied beyond the
  current season.
- **Apply the discount to future years only (`year_offset >= 1`), not
  year 0.** `base_war` (0056's input) comes from `players_run_value`/
  `players_pitching_run_value`, which is `BatterProjection`/
  `PitcherProjection`'s *own* output — already PA/IP-discounted by this
  same injury multiplier for the current season. Discounting year 0 again
  would double-count. Years 1+ come from the age-decline curve alone,
  which has no injury awareness at all — that's the actual gap.
- **Don't compound the multiplier across years.** `prone_overall` describes
  a stable durability trait (expected playing time in a *given* season
  relative to a normal-durability player), not a cumulative decay process.
  Applying the same multiplier fresh to each future year (not raised to
  increasing powers) matches that meaning; compounding would imply
  ever-worsening risk each year, which isn't what the rating represents —
  a "Wrecked" pitcher's 0.76 compounded over 5 years would imply he's
  barely playable by year 5, which the rating doesn't claim.
- **Pitcher role (Starter vs. Reliever).** The multiplier table splits
  pitchers by role, but `get_player_contract_inputs.sql` didn't fetch it and
  `calculate_surplus_value` didn't know if a pitcher was a starter or
  reliever. **Resolved (confirmed with the user):** fetch the role — added
  `players_pitching.role` (joined via `rating_id`, same latest-heap row as
  `pitching_war`) to the query and threaded it through as `pitching_role`,
  mapped 11→Starter, 12/13→Reliever (mirrors `PitcherProjection`'s own
  `ROLE_MAP` in `pitcher.py:49`). A pitcher with a missing/unrecognized role
  value defaults to the `Starter` column (more conservative) rather than
  skipping the discount.

## 3. Approach

- `get_player_contract_inputs.sql`: add `p.prone_overall` to the SELECT
  (and pitcher role, once the outstanding question above is resolved).
- `contract_value.py`: add the injury-category bucketing (mirroring
  `batter.py`/`pitcher.py`'s inline four-line thresholds — small enough
  that duplicating it matches this project's existing per-file style
  rather than introducing a new shared utility module) and the multiplier
  table above as constants. In `calculate_surplus_value`'s loop, multiply
  `year_value` by the appropriate multiplier for every year with
  `year_offset >= 1`.
- Verify against the real `TEST.lg` save (established pattern): confirm a
  known Fragile/Wrecked player's future-year value drops relative to
  before this change, a Durable/Normal player is materially unaffected,
  and year 0 is untouched for everyone.

Verified against the real `TEST.lg` save on the live dev DB (established
pattern; required a backend container restart to pick up the code change —
the dev container doesn't run Flask in debug/reload mode):
- Player 1029 (Wrecked, `prone_overall=200`, Starting Pitcher, role=11,
  2-year signed contract): year 0 value unchanged at $25,982,320; year 1
  dropped from an undiscounted $23,907,320 to a discounted $18,169,563.20 —
  exactly `war × $8.3M × 0.76` (the Wrecked/Starter multiplier).
- Player 21557 (Durable, `prone_overall=0`, batter, 2 years remaining on a
  signed deal): year 1 value moved from an undiscounted -$19,123,117 to
  -$19,505,579.34 — exactly `war × $8.3M × 1.02` (the Durable/Batter
  multiplier), i.e. materially unaffected, matching the "no invented risk
  for durable players" intent.
- Backend suite: 118 passed, including 9 new tests covering year-0
  exclusion, non-compounding across years, missing-`prone_overall`
  fallback, Starter/Reliever role mapping (roles 11/12/13), unknown-role
  default, and a route-level Wrecked-vs-Normal comparison.

**Files involved:**
- `backend/app/db/sql_scripts/api/get_player_contract_inputs.sql` (modified —
  `prone_overall` + `players_pitching.role` join)
- `backend/app/player_projection/contract_value.py` (modified — injury
  multiplier constants, bucketing, and the projection-loop discount)
- `backend/app/api/players.py` (modified — pass `prone_overall`/
  `is_pitcher`/`pitching_role` through to `calculate_surplus_value`)
- `backend/tests/player_projection/test_contract_value.py` (modified)
- `backend/tests/api/test_players.py` (modified)
