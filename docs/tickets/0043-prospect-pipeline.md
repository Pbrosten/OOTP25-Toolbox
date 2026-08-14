# 0043 — Prospect Pipeline

- **Tag:** feat
- **Status:** Open
- **Depends on:** —
- **Blocks:** —

## 1. Problem

`docs/improvements/expanded-functionality.md`'s Tier 1 #6 wants the farm
system treated as a development pipeline, not a static ranking: prospect
performance, age relative to league/level, current level, projection,
development trajectory, ETA, position, future role, risk, organizational
depth at position, and promotion readiness — surfacing prospects ready for
promotion, prospects falling behind, organizational bottlenecks, excess
prospect types, positions lacking future talent, and prospects whose value
makes them viable trade assets. Also explicitly modeled on FanGraphs' Surplus
Value framework, same reference point as
[0042](0042-contract-arbitration-analyzer.md).

There's no prospect-specific view or query anywhere in the app today — no
"is this player a prospect" flag, no level/affiliate concept (see Outstanding
below, same gap [0039](0039-roster-optimization-org-depth.md) hit), and no
ETA/readiness computation.

Filed as an epic-tracker ticket, standalone (no other stagged functionality
in the source doc shares the Farm System IA branch). Related:
[0045](0045-remove-mlb-percentile-toggle.md) removes the (broken) MLB-vs-MiLB
percentile comparison toggle from `BatterPercentiles.vue`/
`PitcherPercentiles.vue` and stops rendering percentiles for non-MLB players
altogether, explicitly deferring proper prospect-cohort percentile comparison
to this epic rather than fixing the toggle in place.

## 2. Design choices

- **Outstanding — no minor-league level/affiliate data.** Same gap as
  [0039](0039-roster-optimization-org-depth.md): `teams` has no level/
  affiliate column, so "current level" and "organizational depth at
  position" (which needs grouping players across an org's full affiliate
  chain, not just one `team_id`) can't be built without first resolving
  where that data comes from in the OOTP export. This is very likely the
  same underlying fix as 0039's version of this question — worth resolving
  once, not twice, whichever ticket starts first.
- **Outstanding — "prospect" definition.** Nothing currently flags a player
  as a prospect vs. a rostered MLB player. Likely inferable from age +
  level + service-time-adjacent signals once those exist, or the OOTP export
  may carry an explicit prospect/potential-grade field not currently
  ingested — needs checking against a real dump.
- **Outstanding — ETA and promotion-readiness scoring.** No defined
  methodology in the source doc for translating ratings + performance +
  age-relative-to-level into an ETA or a readiness flag. Genuinely open
  design question, analogous to how
  [0026](0026-pitcher-projection-methodology.md) needed its own methodology
  pass before implementation could start.
- **Outstanding — surplus-value framework reuse.** The source doc points at
  the same FanGraphs Surplus Value model as
  [0042](0042-contract-arbitration-analyzer.md). If 0042 builds a general
  surplus-value module, this ticket should reuse it (prospects are just
  players with high uncertainty/long time horizon, not a fundamentally
  different value calculation) rather than building a parallel one. Not
  decided which lands first or how tightly coupled they should be.
- **Resolved — underlying ratings/trajectory data mostly exists.** Age,
  position, and rating history (`players_rating` snapshots over time,
  `players_batting`/`players_pitching`/`players_fielding_position`) are
  already ingested per heap — the trajectory/trend half of this (distinct
  from level/ETA/readiness) is buildable today, and overlaps significantly
  with [0044](0044-player-development-monitor.md) (Player Development
  Monitor)'s "track ratings changes over time" scope. That ticket's
  trend-computation layer, once built, is a natural input here rather than
  something this ticket should duplicate.

## 3. Approach (epic outline — needs further breakdown before implementation)

- Resolve the level/affiliate data gap first (shared with 0039) — it blocks
  most of this ticket's org-depth scope.
- Once [0044](0044-player-development-monitor.md)'s trend/delta computation
  exists, reuse it here for "development trajectory" rather than
  reimplementing snapshot-diffing.
- Backend: a prospect-scoped query layer (age/level/position filters over
  the existing rating + WAR tables), plus whatever ETA/readiness scoring
  comes out of the Outstanding methodology question.
- Frontend: a farm-system view per the source doc's suggested
  `FARM SYSTEM › Prospect Pipeline` IA placement.

**Files involved:**
- TBD once broken into sub-tickets and the level/affiliate + methodology
  questions are resolved.
