# 0072 — Risk-adjust FV/surplus value for high-potential/low-overall prospects

- **Tag:** feat
- **Status:** Closed
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

Resolved via a direct design conversation with the user, which changed
the mechanism from the original framing (a silent numeric discount) to a
visible tag:

- **Resolved — risk-adjustment mechanism: a visible "+"/"-" tag, not a
  numeric discount.** `fv`, `expected_war`, `surplus_value`, and
  `star_odds` all stay pure lookups off the talent-ceiling `fv` grade,
  completely unchanged by this ticket. Instead, a new `risk_tag` field
  ("+" | "-" | `null`) surfaces the `fv`/`current_fv` gap directly as a
  visible signal next to the FV badge, so a GM sees the reasoning rather
  than an opaque adjusted number. Chosen over discounting the dollar
  figures (the ticket's original framing) or blending `current_fv` into
  the FV grade itself — both would have changed numbers the user already
  reviews without an obvious explanation for why they moved.
- **Resolved — independent of `prone_overall` injury risk.** "Far from
  talent ceiling" (development risk, this ticket) and "injury-prone"
  (durability risk, 0059's `INJURY_MULTIPLIERS`) stay two separate
  concepts — the tag is driven purely by the `fv`/`current_fv` gap, not
  combined with `prone_overall`. Confirmed directly after an initial
  ambiguity: the user's first-pass answer to "should this reuse
  `INJURY_MULTIPLIERS`" was about reusing that *style* of bucketed
  threshold table, not about folding injury risk into the same signal.
- **Resolved — one shared threshold set for hitters and pitchers.** No
  separate hitter/pitcher curves for v1 — same rationale as 0056's
  placeholder constants: no real save data yet to calibrate two curves
  against, so one shared, explicitly-tunable threshold pair is enough.
- **Resolved — thresholds (placeholder, tunable later, same convention as
  0056's age-decline curve / 0059's injury multipliers):** `RISK_TAG_HIGH_GAP
  = 20` (→ "-"), `RISK_TAG_LOW_GAP = 5` (→ "+"), everything in between
  untagged. FV tiers step in 5s/10s, so a 20+-point gap is roughly 2-3+
  tiers of distance-to-ceiling; a <=5-point gap means current form is
  already at or one tier from the ceiling grade.

## 3. Approach

- `backend/app/player_projection/prospect_value.py`: new
  `RISK_TAG_HIGH_GAP`/`RISK_TAG_LOW_GAP` constants and `_risk_tag(fv,
  current_fv)`, called from both `calculate_hitter_prospect_value` and
  `calculate_pitcher_prospect_value`, adding `"risk_tag"` to their return
  dicts alongside the existing `fv`/`current_fv`/etc.
- `backend/app/api/prospects.py`: `_value_for` passes `risk_tag` through
  into both `GET /api/prospects`' per-row `value` object and
  `GET /api/prospects/<player_id>`'s flattened response — no new query,
  the underlying calc already ran.
- `backend/docs/openai.yaml`: documented `risk_tag` on both endpoints.
- `frontend/src/views/ProspectPipeline.vue`: FV badge now renders
  `{{ fv }} {{ risk_tag }}` (e.g. "55 -") with a tooltip explaining the
  tag.
- `frontend/src/components/SurplusValue.vue`: same treatment on the
  player-page Prospect Value block's FV square badge.
- `backend/tests/player_projection/test_prospect_value.py`: boundary
  tests for `_risk_tag` (high/low/middle gap, exact threshold values) plus
  integration tests confirming both `calculate_*_prospect_value` functions
  include a correct `risk_tag`.

**Verified against real data** (backend container restarted to pick up
the change):
- `GET /api/prospects?team_id=28` (Texas Rangers): real distribution of
  139 "+", 46 untagged, 20 "-" across available prospects — not a flat
  default.
- `GET /api/prospects/138746` (Cris Ortega, `fv=70`/`current_fv=30`, gap
  40): `"risk_tag": "-"`, correctly flagging him as a long-ceiling bet
  despite his elite FV grade.
- Both modified `.vue` files compile cleanly through Vite's SFC transform.
- Full backend suite: 179/179 passing.

**Files involved:**
- `backend/app/player_projection/prospect_value.py` (modified)
- `backend/app/api/prospects.py` (modified)
- `backend/docs/openai.yaml` (modified)
- `frontend/src/views/ProspectPipeline.vue` (modified)
- `frontend/src/components/SurplusValue.vue` (modified)
- `backend/tests/player_projection/test_prospect_value.py` (modified)

## 4. Follow-up (same session, user request): the tag also modifies
surplus_value/star_odds

After the tag-only version shipped, the user asked for the tag to also
scale `surplus_value`/`star_odds` numerically — reversing this ticket's
earlier "visible tag, not a discount" resolution back toward (but not
identical to) the original problem statement's framing.

- New `RISK_TAG_MODIFIERS = {"+": 1.10, "-": 0.70, None: 1.0}` and
  `_apply_risk_modifier(value, risk_tag)` in `prospect_value.py`, applied
  to `_fv_to_value`'s output in both `calculate_hitter_prospect_value` and
  `calculate_pitcher_prospect_value`, before the risk-modified dict is
  merged into the return value.
- **`fv`/`expected_war` still untouched** — only `surplus_value`/
  `star_odds` are scaled, preserving this ticket's original distinction
  between the pure talent-ceiling grade and the dollar/probability
  outputs. `expected_war` in particular stays the FanGraphs source
  table's own number for that FV tier, not something this app derived.
- `star_odds` is capped at 100.0 after the premium multiplier, so a
  high-base tier (e.g. FV 70's 87.5%) can't be pushed into a nonsensical
  above-100% "probability" by the "+" boost.
- Placeholder values (1.10/0.70), explicitly tunable later, same
  convention as `RISK_TAG_HIGH_GAP`/`RISK_TAG_LOW_GAP` and 0056/0059's
  constants.
- 8 new tests: 4 pure `_apply_risk_modifier` unit tests (discount, boost,
  untagged no-op, star_odds cap) + 4 integration tests confirming both
  `calculate_*_prospect_value` functions apply the modifier correctly and
  leave `expected_war` alone.

**Verified against real data** (backend container restarted again):
- Cris Ortega (FV 70, risk_tag "-"): `surplus_value` $195M → $136.5M,
  `star_odds` 87.5% → 61.2% (both exactly the base FV-70 row × 0.70,
  banker's-rounded).
- Erik Parker (FV 55, risk_tag "-"): $55M → $38.5M, 17.5% → 12.2% (same
  0.70× discount, different base tier).
- Both `.vue` files still compile cleanly (no template changes needed --
  they already render whatever `surplus_value`/`star_odds` the API
  returns).
- Full backend suite: 185/185 passing.

## 5. Follow-up (same session, user request): exclude FV 30 players from
the Prospect Pipeline entirely

FV 30 ("Up & Down") is the bottom reachable tier -- already `$0`/`0.0%`
under `_fv_to_value`'s below-35 floor before any risk modifier, and (per
0068's Design choices) the biggest single bucket in a full org's org-depth
players. The user asked to stop listing them at all rather than showing a
wall of zero-value rows.

- New `EXCLUDED_FV = {30}` and `_is_excluded(value)` in
  `backend/app/api/prospects.py`, checked right after `_value_for(row)` in
  both `get_prospects()` (skips appending the row *and* skips the
  now-wasted `_trend_for` call for it -- a small perf win on top of the
  filtering) and `get_prospect_value()` (returns `{"is_prospect": false}`
  instead, same as a player who never qualified at all -- consistent with
  0071's player-page fallback to contract-based surplus value).
- No SQL change -- FV is a Python-computed talent-ceiling projection, not
  a raw column, so the exclusion can only happen after `_value_for` runs.
- 2 new tests: `test_get_prospects_excludes_fv30_players` (list route, via
  a new `_fv30_row()` fixture with bottom-of-scale ratings across the
  board) and `test_get_prospect_value_excludes_fv30_player` (single-player
  route).

**Verified against real data** (backend container restarted again):
- `GET /api/prospects?team_id=28` (Texas Rangers): dropped from 197 to 86
  prospects; confirmed `fv=30` no longer appears anywhere in the response
  (distribution now 40/45/50/55/60/70 only).
- `GET /api/prospects/46056` (Dax Hardcastle, previously `fv=30`):
  `{"is_prospect": false}`.
- Full backend suite: 187/187 passing.
