# 0043 — Prospect Pipeline

- **Tag:** feat
- **Status:** In-Progress
- **Depends on:** [0044](0044-player-development-monitor.md)
- **Blocks:** [0038](0038-gm-command-center.md)

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
"is this player a prospect" flag and no ETA/readiness computation. (There
*was* no level/affiliate concept either when this ticket was first filed —
see Resolved below, that gap closed under 0039's epic before this ticket
started.)

Filed as an epic-tracker ticket, standalone (no other stagged functionality
in the source doc shares the Farm System IA branch). Related:
[0045](0045-remove-mlb-percentile-toggle.md) removes the (broken) MLB-vs-MiLB
percentile comparison toggle from `BatterPercentiles.vue`/
`PitcherPercentiles.vue` and stops rendering percentiles for non-MLB players
altogether, explicitly deferring proper prospect-cohort percentile comparison
to this epic rather than fixing the toggle in place.

## 2. Design choices

All resolved via a direct design conversation with the user (per this
project's convention of asking rather than unilaterally deciding
outstanding/judgment-call questions).

- **Resolved — level/affiliate data gap closed by 0039's epic.** `teams`
  now carries `parent_team_id`/`level` ([0062](0062-team-level-affiliate-schema-migration.md)),
  and a working org-scoped query
  (`backend/app/db/sql_scripts/api/get_org_depth_chart.sql`, from
  [0063](0063-roster-depth-chart-query-api.md)) already exists to reuse for
  "organizational depth at position" instead of building a parallel query.
- **Resolved — "prospect" definition.** A player is a prospect if `age <
  26` **AND** (`teams.level != 1` (currently on any non-MLB affiliate), OR
  `teams.level == 1 AND players_service_time.mlb_service_years == 0`
  (catches a just-debuted rookie who's still prospect-relevant for trade/
  roster purposes)). Uses data from 0062 and
  [0053](0053-contract-service-time-schema.md)/[0054](0054-contract-service-time-migration.md),
  both already ingested.
  - **Post-close correction to 0069 (user report):** the age gate was
    added after 0069 shipped without one -- level/service-time alone let a
    veteran journeyman briefly optioned back to AAA (real case: a
    32-year-old reliever) show up as a "prospect." `age < 26` is an
    additional gate on top of, not instead of, the level/service-time
    check. Implemented directly in `get_prospects.sql`, no new ticket
    (user's explicit call).
- **Resolved — development trajectory reuses 0044's trend layer.**
  [0044](0044-player-development-monitor.md)'s sliding-3-heap-lookback
  delta computation ([0050](0050-rating-trend-query-layer.md)) is a direct
  input here, not reimplemented.
- **Resolved — "Overall talent" / value methodology (FanGraphs Future
  Value framework, replicated against this app's own data).** Sourced from
  two FanGraphs articles the user pointed to
  ("[The New FanGraphs Scouting Primer](https://blogs.fangraphs.com/the-new-fangraphs-scouting-primer/)",
  "[Introducing an Updated Method for Prospect Valuation](https://blogs.fangraphs.com/introducing-an-updated-method-for-prospect-valuation/)")
  plus two reference tables the user supplied directly (a role/WAR-to-FV
  scale image, and a FV-to-surplus-value/WAR/star-odds table image). The
  full pipeline, resolved question by question:
  - **Talent-ceiling projection.** Feed `BatterProjection`/
    `PitcherProjection` (reused as-is, no new weighting scheme) with
    **talent (potential) ratings substituted for current ratings**, for
    the categories that actually have a talent/potential grade in OOTP:
    `players_batting_talent` (contact/gap/eye/strikeouts/power/babip),
    `players_pitching_talent` (stuff/movement/control/hra/pbabip/...), and
    `players_fielding_position_talent` (pos1-9 — OOTP does model
    positional fitness as developing, unlike the skill components below).
    Everything else the projection classes need — speed, steal,
    baserunning (`players_basepath`), and the core defensive skill
    ratings (catcher/infield/outfield arm, range, error —
    `players_fielding`) — **stays sourced from current ratings**, because
    OOTP has no talent/potential version of those (confirmed: no
    `players_basepath_talent` table, no `players_fielding_talent` table
    for the skill components, only for position fitness). This produces
    an annual talent-ceiling projected WAR per prospect.
  - **WAR → FV grade.** Bucket that annual WAR into a 20-80 Future Value
    grade via separate hitter/pitcher role tables (full tiers only: 20,
    30, 40, 45, 50, 55, 60, 70, 80):
    - Hitter: 20 Org guy (—) · 30 Up & Down (<-0.1) · 40 Bench Player
      (0.0-0.7) · 45 Low-End Reg/Platoon (0.8-1.5) · 50 Avg Everyday
      Player (1.6-2.4) · 55 Above-Avg Reg (2.5-3.3) · 60 All-Star
      (3.4-4.9) · 70 Top-10 overall (5.0-7.0) · 80 Top-5 overall (>7.0).
    - Pitcher (starters only — see below): 20 Org Guy (—) · 30 Up & Down
      (<-0.1) · 40 Backend starter (0.0-0.9) · 45 #4/5 starter (1.0-1.7)
      · 50 #4 starter (1.8-2.5) · 55 #3/4 starter (2.6-3.4) · 60 #3
      starter (3.5-4.9) · 70 #2 starter (5.0-7.0) · 80 Ace (>7.0).
  - **FV grade → surplus value / expected WAR / star odds**, from the
    user-supplied table (exact figures, half-tiers included though
    unreachable by the WAR→FV lookup above since that only produces full
    tiers — kept in the constant table for completeness, simply unused
    for now):

      | FV | Hitter $ / WAR / Odds | Pitcher $ / WAR / Odds |
      |----|------------------------|-------------------------|
      | 70 | $195M / 27.5 / 87.5% | $195M / 27 / 87.5% |
      | 65 | $95M / 13.5 / 40.0% | $95M / 13.5 / 40.0% |
      | 60 | $82M / 12.5 / 33.0% | $70M / 11 / 21.0% |
      | 55 | $55M / 8 / 17.5% | $45M / 7 / 7.0% |
      | 50 | $45M / 7 / 13.5% | $33.5M / 5 / 7.0% |
      | 45+ | $18.5M / 3.2 / 6.0% | $15M / 2.6 / 3.0% |
      | 45 | $14.5M / 2.5 / 3.5% | $9.5M / 1.6 / 1.5% |
      | 40+ | $8M / 1.2 / 1.8% | $7M / 1 / 1.0% |
      | 40 | $5.5M / 0.75 / 0.8% | $4M / 0.55 / 0.4% |
      | 35+ | $2M / 0.3 / 0.4% | $1.5M / 0.25 / 0.4% |

  - **Edge cases (no source data at these tiers):** FV 80 uses the FV 70
    row's dollar value as a conservative floor (no published data above
    70). FV grades below 35 (i.e. 20/30 — "Org guy"/"Up & Down") get $0
    surplus value rather than an invented number, consistent with the
    primer's own framing that these tiers carry no real trade value.
  - **Relief pitchers: no exclusion, no separate table (post-close
    correction to this original decision, user request).** Originally
    excluded from FV/value scoring — see 0068's post-close correction
    section for the full reversal. A real-data review found ~27% of a
    full org's pitching prospects coming back "not available" this way;
    reconsidered because `PitcherProjection`'s own role-specific baseline
    constants (RP's much smaller PA/IP workload) already produce a
    meaningfully lower annual WAR for a reliever than a starter at
    equivalent ratings, so applying the same starters-calibrated
    `PITCHER_WAR_TO_FV` table to RP naturally sorts them into lower FV
    tiers rather than needing a hard exclusion.
  - **This is a new, separate calculation from 0042/0056's contract
    surplus value** — that model nets a *signed contract's* actual salary
    against WAR and needs `players_contract`/`players_service_time`,
    which most true prospects don't have. Prospects get their own
    FV-based value model instead of forcing them through 0056's calc.
- **Resolved — MLB promotion readiness reuses the same WAR→FV lookup, fed
  current ratings instead of talent, scoped to MLB promotion only.** Run
  the identical projection + WAR→FV bucketing above, but with **current**
  (not talent) ratings, to get a present-day role tier. If that current-form
  tier is FV 40 ("Bench Player"/"Backend starter") or better while the
  player is still below `level = 1`, that's the "ready for MLB promotion"
  signal. Explicitly scoped to *promotion to the majors only* — not used
  for intermediate level-to-level movement (e.g. A → AA), which stays
  out of scope. Avoids inventing a separate per-level WAR bar with no data
  source behind it.

## 3. Approach

Broken into three sub-tickets, mirroring the layering used by 0044/0056/0062:

```
[~] 0068 Prospect FV/value calculation module
      |
      v
[ ] 0069 Prospect query layer + API route
      |
      v
[ ] 0070 Prospect Pipeline frontend view

[~] = In-Progress   [ ] = Open   [x] = Closed
```

- [0068](0068-prospect-fv-value-calculation.md) — the calculation module:
  talent-ceiling projection (talent ratings in, current ratings for the
  non-developing categories), the WAR→FV lookup tables, the FV→surplus
  value/expected WAR/star-odds table, and the current-ratings MLB-promotion
  readiness flag. Pure calculation, no new schema (mirrors 0056's "computed
  at read time" precedent) — reuses `BatterProjection`/`PitcherProjection`
  as-is.
- [0069](0069-prospect-query-layer-api.md) — the prospect-scoped query
  layer + API route: the prospect definition filter (level/service-time),
  reuses 0063's org-depth query for "organizational depth at position" and
  0050's trend layer for "development trajectory," wraps 0068's calc
  output per player.
- [0070](0070-prospect-pipeline-frontend.md) — the frontend view, per the
  source doc's suggested `FARM SYSTEM › Prospect Pipeline` IA placement.

**Files involved:**
- See each sub-ticket's own Approach section.
