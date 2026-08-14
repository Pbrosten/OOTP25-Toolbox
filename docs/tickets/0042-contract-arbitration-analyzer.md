# 0042 — Contract & Arbitration Analyzer

- **Tag:** feat
- **Status:** In-Progress
- **Depends on:** [0053](0053-contract-service-time-schema.md), [0054](0054-contract-service-time-migration.md)
- **Blocks:** —

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
  out of scope for this epic. **Chosen:** use a fixed, configurable
  placeholder constant for $/WAR (alongside the existing
  `player_projection` constants pattern, e.g. `INJ_CONSTANTS` in
  `backend/app/player_projection/batter.py`) until real in-save free-agent
  signings are ingested; revisit the constant once that data exists. Not a
  blocker for building the surplus-value calculation itself.
- **Recommendation thresholds.** Turning a surplus-value number into a
  categorical Extend/Keep/Let-walk/Non-tender/Trade recommendation needs
  threshold rules the source doc doesn't specify. **Left fully deferred** —
  scoped as its own later sub-ticket once the surplus-value number actually
  exists, not decided here.
- **Aging/injury risk inputs.** "Aging risk" reuses the existing age-curve
  gap flagged in [0026](0026-pitcher-projection-methodology.md)
  (age-development is currently skipped in both `BatterProjection` and
  `PitcherProjection` — current ratings only, no blend). **Chosen:** match
  0041's tentative resolution — current-ratings-only aging (no age-curve
  blend) and `players.prone_overall` as the injury-risk proxy, for v1.
  Revisit both if/when 0026's age-curve gap is resolved upstream.

## 3. Approach (epic outline — needs further breakdown before implementation)

- Contract/salary ingestion: [0053](0053-contract-service-time-schema.md)
  (schema) + [0054](0054-contract-service-time-migration.md) (migration),
  filed as the shared prerequisite for this ticket and 0041.
- Once contract data exists: a surplus-value module (parallel structure to
  `app/player_projection/batter.py`/`pitcher.py`) combining projected WAR
  (already available via `players_run_value`/`players_pitching_run_value`)
  with salary/years-of-control to produce a fair-value range and surplus
  number.
- API + frontend: expose the recommendation on the player detail page
  (`frontend/src/components/PlayerDetails.vue`) per Cross-Cutting Design
  Principle #1 ("From Stats to Decisions") — surface the recommendation
  first, raw surplus number available underneath.

**Files involved:**
- Contract ingestion: see [0053](0053-contract-service-time-schema.md)/
  [0054](0054-contract-service-time-migration.md) for exact files.
- TBD once further broken down — the value model is a new
  `app/player_projection/` module; display touches
  `frontend/src/components/PlayerDetails.vue`.
