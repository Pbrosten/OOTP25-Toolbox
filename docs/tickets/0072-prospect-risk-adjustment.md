# 0072 — Risk-adjust FV/surplus value for high-potential/low-overall prospects

- **Tag:** feat
- **Status:** Open
- **Depends on:** [0068](0068-prospect-fv-value-calculation.md)
- **Blocks:** —

## 1. Problem

Filed from a user report while reviewing the Prospect Pipeline against real
data: 0068's FV grade, surplus value, and star odds are all derived purely
from a **talent-ceiling** projection (potential ratings run through
`BatterProjection`/`PitcherProjection`). Nothing in that calculation
accounts for how far a player's *current* ability is from that ceiling. A
player who's already close to his potential and one with a huge gap between
his current overall and his potential get identical FV/surplus-value/star-
odds today as long as their talent-ceiling WAR matches — even though the
second player is a much riskier bet (more that has to go right in
development for the projection to actually materialize) and real scouting
valuation (including the FanGraphs framework 0068 replicates) treats that
kind of projection uncertainty as a real discount, not a rounding error.

0068 already computes both `fv` (talent-ceiling) and `current_fv`
(current-form) per prospect side by side — today `current_fv` is only used
for the MLB-promotion-readiness flag, but the gap between the two is
sitting right there as a ready-made risk signal, unused for value purposes.

## 2. Design choices

None resolved yet — filed as a scoping ticket per the user's explicit
request, not implemented here.

- **Outstanding — risk-adjustment methodology.** How should the
  `fv`/`current_fv` gap discount `surplus_value`/`star_odds`? Candidate
  shapes: (a) a multiplicative discount curve keyed on gap size (e.g. a
  flat percentage haircut per FV-tier of gap), (b) blend `current_fv` and
  `fv` into a single risk-adjusted grade before doing the `FV_TO_VALUE`
  lookup (rather than adjusting the looked-up dollar figure directly),
  (c) leave `fv`/`expected_war` alone and apply the discount only to
  `surplus_value`/`star_odds`. Needs a real methodology pass, same as
  0026/0056 needed their own before implementation — worth re-reading the
  two FanGraphs source articles (already read for 0043/0068) to check
  whether "star odds" in the source table already implicitly folds in a
  bust-probability/risk concept *by FV tier* that this ticket would be
  double-counting if not careful, versus a genuinely unaddressed
  within-tier risk dimension.
- **Outstanding — overlap with existing risk signals.** `prone_overall`
  (injury-risk proxy) already discounts *contract* surplus value
  elsewhere (0059) via `INJURY_MULTIPLIERS` in `contract_value.py`. Should
  this new development-risk discount reuse that same multiplier
  structure/precedent, or is "far from ceiling" a genuinely distinct risk
  dimension from "injury-prone" that deserves its own separate constant
  set?
- **Outstanding — scope: hitters and pitchers uniformly, or different
  curves?** A pitcher's projection volatility (injury, mechanical
  breakdown) may warrant a different risk curve than a hitter's
  (approach/plate-discipline) — undecided whether this ticket needs two
  separate curves or one shared one is good enough for v1.

## 3. Approach

TBD — blocked on the Outstanding questions above being resolved with the
user before implementation starts.

**Files involved:**
- `backend/app/player_projection/prospect_value.py` (likely) —
  `calculate_hitter_prospect_value`/`calculate_pitcher_prospect_value`
  already compute both `fv` and `current_fv`; risk adjustment applies
  somewhere in that existing pipeline once the methodology is resolved.
- `backend/tests/player_projection/test_prospect_value.py` (test updates).
