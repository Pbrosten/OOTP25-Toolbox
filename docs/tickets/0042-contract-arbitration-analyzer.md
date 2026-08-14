# 0042 — Contract & Arbitration Analyzer

- **Tag:** feat
- **Status:** Open
- **Depends on:** —
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

Nothing in the app touches contracts or salary today — see Outstanding below.

Filed as an epic-tracker ticket. Grouped with
[0041](0041-trade-target-finder.md) (Trade Target Finder) under the same
Transactions-area epic; see that ticket for why they're siblings rather than
a dependency chain despite sharing a data gap.

## 2. Design choices

- **Outstanding — no contract/salary/arbitration data ingested (blocking).**
  Same gap as [0041](0041-trade-target-finder.md): `schema.sql` and
  `staging.py`'s `DUMP_INCLUSION_LIST` have no contract, salary, or
  arbitration table. Unlike Trade Target Finder, this ticket has **no
  reduced-scope fallback** — "should we pay this player" is meaningless
  without knowing what he's currently owed. This ticket cannot start until
  contract/salary data is ingested. That ingestion work isn't scoped here
  (needs a real dump export inspected first to know the raw OOTP table/
  column names) — likely its own prerequisite ticket, shared with 0041.
- **Outstanding — surplus-value formula.** The source doc says "root system
  in a similar system to FanGraphs' Surplus Value" but doesn't specify the
  formula. FanGraphs' public methodology (roughly: projected WAR × $/WAR
  market rate, minus actual salary, discounted for years of control and
  aging) would need adapting to OOTP's in-league economy (its $/WAR rate
  isn't real-world MLB's and would need deriving from in-save free-agent
  signings, which requires the free-agent-market data
  [0041](0041-trade-target-finder.md) also flagged as missing). Not decided.
- **Outstanding — recommendation thresholds.** Turning a surplus-value number
  into a categorical Extend/Keep/Let-walk/Non-tender/Trade recommendation
  needs threshold rules the source doc doesn't specify (e.g. what surplus
  range means "Extend" vs. "Keep short-term"). Deferred design question, not
  a blocker for building the underlying value calculation itself.
- **Outstanding — aging/injury risk inputs.** "Aging risk" could reuse the
  existing age-curve gap already flagged in
  [0026](0026-pitcher-projection-methodology.md) (age-development is
  currently skipped in both `BatterProjection` and `PitcherProjection` —
  current ratings only, no blend). "Injury risk" has the same
  `prone_overall`-as-proxy question raised in
  [0041](0041-trade-target-finder.md). Both need resolving here or upstream
  before a real risk-adjusted value model is possible.

## 3. Approach (epic outline — needs further breakdown before implementation)

- Contract/salary ingestion is the actual first step and isn't scoped by
  this ticket — inspect a real dump export's staging tables (the way
  [0029](0029-pitcher-pitch-repertoire.md) inspected `players_pitching`'s
  per-pitch columns) to find what OOTP exports for contracts/arbitration,
  then file schema + migration tickets mirroring the
  [0024](0024-pitcher-schema-ratings-tables.md)/[0025](0025-pitcher-migration-ingestion.md)
  pattern.
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
- TBD once broken into sub-tickets — contract ingestion touches `schema.sql`,
  `staging.py`, and migration SQL; the value model is a new
  `app/player_projection/` module; display touches
  `frontend/src/components/PlayerDetails.vue`.
