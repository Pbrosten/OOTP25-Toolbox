# 0058 — Contract recommendation thresholds

- **Tag:** feat
- **Status:** Closed
- **Depends on:** [0056](0056-surplus-value-calculation.md)
- **Blocks:** —

## 1. Problem

[0042](0042-contract-arbitration-analyzer.md)'s original ask was a
recommendation — Extend / Keep short-term / Let walk / Non-tender / Trade
before free agency — not just a raw surplus number. 0056/0057 built and
displayed the number; this ticket turns it into the label, closing 0042's
last explicitly-deferred gap.

## 2. Design choices

- **Threshold basis: a curated cohort, not the full player pool.**
  Attempting to derive thresholds from every rated player in the save
  produced nonsense (median surplus/year ≈ **-$23M**, 90th percentile still
  negative) — traced to the save having **259 teams**, so the full
  `players` pool is dominated by organizational depth that was never going
  to be MLB-caliber, not a `BatterProjection`/`PitcherProjection`
  calibration bug (confirmed: restricting to real, meaningfully-salaried
  contracts — `players_contract.salary0 > $1,000,000` — flips the
  distribution to a sane 22% negative, median WAR 1.2). **Chosen:** derive
  threshold cutoffs from that same curated cohort (`years > 0 AND salary0 >
  $1,000,000`, n=611 in `TEST.lg`): average-surplus-per-year distribution —
  p30 ≈ -$5.6M, p50 ≈ -$1.4M, p70 ≈ +$4.4M/yr. `years_covered` median 2
  (range 1-7, heavily weighted toward 1-3 years left).
- **Metric: average surplus per year, not total.** Confirmed with the
  user — normalizes across different horizon lengths so a great
  one-year rental doesn't look worse than a mediocre five-year deal just
  because its total is smaller.
- **Two-axis decision: years-of-control-remaining × surplus/year tier.**
  Confirmed with the user. `years_remaining = len(years)` from 0056's
  output; surplus/year tiers use a single **$5,000,000/yr** cutoff (rounded
  from the p70 ≈ $4.4M finding above) to separate "strongly positive" from
  "merely positive," and $0 as the positive/negative breakeven. Final
  table:

  | years remaining | surplus/yr ≥ $5M | $0 to $5M | < $0, discretionary | < $0, guaranteed |
  |---|---|---|---|---|
  | ≤ 1 | Trade before FA | Trade before FA | Let walk | Let walk |
  | ≥ 2 | Extend | Keep short-term | Non-tender | Let walk |

  "Discretionary" vs. "guaranteed" checks the whole projected horizon, not
  just the upcoming season — see the post-implementation correction below
  on why `years[0]` alone was wrong.
- **New per-year `source` field, required for the guaranteed/discretionary
  split.** 0056's output didn't distinguish which years came from a real
  signed contract vs. a projected pre-arb/arbitration estimate. Added
  `source: "contract" | "pre_arb" | "arbitration"` to each year entry in
  `calculate_surplus_value`'s output — a direct label of which branch
  already-existing code took, not new logic. `has_received_arbitration`
  (ingested in 0053/0054, never used until now) isn't needed for this —
  `source` already captures the distinction from the existing branch
  structure.
- **`recommendation` is `None` when there's nothing to act on.** Same
  "not available" contract as 0056/0057 — a two-way player, a player with
  no current WAR, etc. never reaches this logic at all (0056 already
  returns `None`/`{"available": false}` for those). No new "unavailable"
  state needed here.

## 3. Approach

`backend/app/player_projection/contract_value.py`:

```python
RECOMMENDATION_EXTEND_THRESHOLD = 5_000_000  # $/yr, rounded from p70 (~$4.4M)
                                              # in the curated-cohort derivation
                                              # above -- tune against more data later.

def recommend_contract_action(result):
    """result: calculate_surplus_value's return value (not None)."""
    years = result["years"]
    years_remaining = len(years)
    avg_surplus = result["total_surplus"] / years_remaining
    discretionary = any(yr["source"] != "contract" for yr in years)

    if years_remaining <= 1:
        return "Trade before free agency" if avg_surplus >= 0 else "Let walk"
    if avg_surplus >= RECOMMENDATION_EXTEND_THRESHOLD:
        return "Extend"
    if avg_surplus >= 0:
        return "Keep short-term"
    return "Non-tender" if discretionary else "Let walk"
```

Add `"source"` to each year dict in `calculate_surplus_value` (`"contract"`
in the `under_contract` branch, `"pre_arb"` / `"arbitration"` in the two
branches of the existing `else`) — no other logic changes.

`backend/app/api/players.py`'s `/surplus-value` route: call
`recommend_contract_action(result)` and add `"recommendation"` to the JSON
response alongside the existing fields.

`frontend/src/components/SurplusValue.vue`: render the recommendation as a
badge above the existing summary tiles (color per label — e.g. teal for
Extend/Keep, amber for Trade/Let-walk, red for Non-tender — matching the
existing surplus-sign color convention rather than inventing a new palette).

Verified against the real `TEST.lg` save on the live dev DB (established
pattern): Cole Young (41335, strong young value) → "Extend"; a real
escalating multi-year contract (810) → "Extend"; player 49952 (Jarlin
Susana, the arbitration bug report from earlier) → "Non-tender". Re-swept
player IDs 1-3000: 387 available, 0 errors; recommendation distribution
skewed heavily toward "Non-tender" (318/387) — consistent with, not a
regression from, the earlier finding that this 259-team save's raw
player-ID range is mostly organizational depth with genuinely negative
surplus value. Backend suite: 107 passed (7 new
`recommend_contract_action` tests).

**Bug found and fixed during this verification:** the initial
`discretionary = years[0]["source"] != "contract"` check used only the
*current* year to decide guaranteed-vs-discretionary. For player 49952 —
a real `years=1, current_year=0` arb-1 deal, i.e. **already** signed and
tendered for the current season — `years[0]["source"]` is `"contract"`
(the team is committed to this year regardless), so the check said
"guaranteed" and returned "Let walk" instead of "Non-tender", even though
years 1 and 2 both reverted to `"arbitration"` (the team genuinely could
walk away after this season). **Fixed:** check the whole horizon —
`discretionary = any(yr["source"] != "contract" for yr in years)` — since
"can the team walk away" should ask whether *any* point before the
horizon ends is discretionary, not just the immediate year (which, for an
already-tendered arb season, is definitionally never discretionary).
Added a regression test
(`test_recommend_negative_surplus_signed_current_year_still_non_tender`)
pinned to this exact scenario.

**Post-implementation scope narrowing, per user report:** the
recommendation was originally shown for every "available" player
regardless of service time — including established veterans years past
free agency (like player 810, already on a real multi-year deal) and
pre-arb rookies, for whom Extend/Non-tender/etc. isn't really the live
decision the label set describes. **Fixed:** `/surplus-value` now only
includes `"recommendation"` in its response when the player's current
`mlb_service_years` falls inside the arbitration window
(`ARB_ELIGIBLE_SERVICE_YEARS <= mlb_service_years < FA_SERVICE_YEARS`,
i.e. 3-5 years). No frontend change needed — `SurplusValue.vue`'s
`v-if="recommendation"` already treats an absent field as "don't show the
badge," the same way it already treats `null`. Re-verified: player 810
(an established veteran outside the window) no longer shows a
recommendation; Cole Young and player 49952 (both inside the window)
still do. Re-swept player IDs 1-3000: 387 available (unchanged), of which
only 65 now carry a recommendation (down from all 387) — 0 errors. Added
two route-level tests
(`test_get_player_surplus_value_pre_arb_omits_recommendation`,
`test_get_player_surplus_value_past_free_agency_service_omits_recommendation`).

**Files involved:**
- `backend/app/player_projection/contract_value.py` (modified — `source`
  field, `recommend_contract_action`)
- `backend/app/api/players.py` (modified — include `recommendation` in the
  route response, gated to the arbitration-eligible service-time window)
- `frontend/src/components/SurplusValue.vue` (modified — recommendation
  badge)
- `backend/tests/player_projection/test_contract_value.py` (modified — new
  tests for `recommend_contract_action`)
- `backend/tests/api/test_players.py` (modified — arb-eligibility gate
  tests)
