# 0042 — Contract & Arbitration Analyzer

- **Tag:** feat
- **Status:** In-Progress
- **Depends on:** [0053](0053-contract-service-time-schema.md), [0054](0054-contract-service-time-migration.md)
- **Blocks:** [0056](0056-surplus-value-calculation.md), [0057](0057-surplus-value-frontend-display.md)

## 1. Problem

`docs/improvements/expanded-functionality.md`'s Tier 1 #5 asks "should we pay
this player, and how much is he worth?" — projected value/WAR, salary
projections, arbitration estimates, free-agent market comparisons, contract
scenario modeling, surplus value, aging/injury risk, and a probability the
contract becomes inefficient — surfaced as a recommendation (Extend / Keep
short-term / Let walk / Non-tender / Trade before free agency) with a
fair-value range and projected surplus, explicitly modeled on FanGraphs'
Surplus Value framework.

Nothing in the app touches contracts or salary today — see Design choices
below.

Filed as an epic-tracker ticket. Grouped with
[0041](0041-trade-target-finder.md) (Trade Target Finder) under the same
Transactions-area epic; see that ticket for why they're siblings rather than
a dependency chain despite sharing a data gap.

## 2. Design choices

- **No contract/salary/arbitration data ingested (blocking).** Same gap as
  [0041](0041-trade-target-finder.md). **Resolved:** inspected a real dump
  export (`TEST.lg` save) and found `players_contract`,
  `players_salary_history`, and the service-time/arbitration fields on
  `players_roster_status` all exist in the raw OOTP export. Filed as the
  shared prerequisite [0053](0053-contract-service-time-schema.md) (schema)
  and [0054](0054-contract-service-time-migration.md) (migration
  ingestion), mirroring the 0024/0025 pattern; both block this ticket and
  0041's full-scope pass. (A `players_contract_extension` table also
  exists in the raw export but was deliberately left uningested — 0053
  found this pipeline's yearly-only refresh cadence means any extension
  it captures is already stale or already folded into `players_contract`
  by the next snapshot, so "extend" scenario modeling for this ticket
  works off `players_contract`'s own option/opt-out fields, not a separate
  pending-extension record.)
- **Surplus-value $/WAR market rate.** FanGraphs' public methodology derives
  its $/WAR rate from real free-agent signings — OOTP's in-save equivalent
  needs the free-agent-market data 0041 also flagged as missing, which is
  out of scope for this epic. **Resolved in
  [0056](0056-surplus-value-calculation.md):** rather than an arbitrary
  placeholder, derived a starting estimate directly from real
  `players_contract`/WAR data in the `TEST.lg` save (median implied $/WAR
  across market-rate contracts ≈ $8.3M) — a documented, swappable constant,
  not a guess. Not a blocker for building the calculation itself; revisit
  once real free-agent-market signings are ingested.
- **Recommendation thresholds.** Turning a surplus-value number into a
  categorical Extend/Keep/Let-walk/Non-tender/Trade recommendation needs
  threshold rules the source doc doesn't specify. **Left fully deferred** —
  scoped as its own later sub-ticket once the surplus-value number actually
  exists, not decided here.
- **Aging/injury risk inputs.** Two distinct things ended up decided
  separately. "Aging" at the *rating-projection* level (`BatterProjection`/
  `PitcherProjection`'s own output) still has no age-curve blend — that gap
  (shared with [0026](0026-pitcher-projection-methodology.md)) is untouched.
  But surplus value's own *forward-looking* WAR-over-multiple-years
  projection needed its own age-decline curve regardless (a flat WAR
  assumption across a 6+ year control window was rejected during
  0056's design discussion) — see 0056 for the chosen slow-then-harsh
  decline coefficients, scoped only to this calculation, not to the rating
  projections themselves. "Injury risk" still matches 0041's tentative
  resolution — `players.prone_overall` as the proxy — and isn't yet wired
  into 0056's calculation at all (0056 doesn't apply an injury discount;
  that remains open for a future revision).

## 3. Approach (epic outline — broken down into sub-tickets below)

- Contract/salary ingestion: [0053](0053-contract-service-time-schema.md)
  (schema) + [0054](0054-contract-service-time-migration.md) (migration),
  filed as the shared prerequisite for this ticket and 0041. **Closed.**
- Surplus-value calculation module + API route:
  [0056](0056-surplus-value-calculation.md) — combines projected WAR
  (already available via `players_run_value`/`players_pitching_run_value`)
  with contract salary and a years-of-control/aging model to produce a
  fair-value total, cost total, and surplus number per player.
- Frontend display: [0057](0057-surplus-value-frontend-display.md) —
  surfaces the raw numbers on the player detail page
  (`frontend/src/components/PlayerDetails.vue`), per Cross-Cutting Design
  Principle #1 ("From Stats to Decisions"). No recommendation label yet —
  that's the still-deferred thresholds question above; this shows the
  underlying value/cost/surplus figures a recommendation would eventually
  be derived from.
- Not yet ticketed: the recommendation-threshold layer (deferred design
  question above) that would turn 0056's surplus number into an
  Extend/Keep/Let-walk/Non-tender/Trade label.

**Files involved:**
- Contract ingestion: see [0053](0053-contract-service-time-schema.md)/
  [0054](0054-contract-service-time-migration.md) for exact files.
- Surplus-value calc + API: see
  [0056](0056-surplus-value-calculation.md) for exact files.
- Frontend display: see
  [0057](0057-surplus-value-frontend-display.md) for exact files.
