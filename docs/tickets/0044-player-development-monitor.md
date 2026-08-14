# 0044 — Player Development Monitor

- **Tag:** feat
- **Status:** In-Progress
- **Depends on:** —
- **Blocks:** —

## 1. Problem

`docs/improvements/expanded-functionality.md`'s Tier 1 #7 wants the app to
detect meaningful changes in player ability/performance over time — tracking
monthly/yearly changes in offensive/pitching/defensive ratings, speed,
stuff/movement/control, actual vs. projected performance, and age-relative
development/decline — surfacing alerts like "contact ability has improved
substantially and production has followed" or "veteran pitcher's stuff and
velocity are declining faster than expected."

This is the one stagged functionality in this document that's buildable
almost entirely from data the app already ingests: `players_rating` is
uniquely keyed on `(player_id, rating_date)`
(`backend/app/db/sql_scripts/schema.sql:177-184`), so every monthly/yearly
heap already produces a new snapshot row per player, and
`players_batting`/`players_pitching`/`players_fielding`/`players_basepath`
all carry the underlying rating values per snapshot. Nothing currently reads
across snapshots to compute a delta or trend, though — every existing
consumer (`PercentileBar.vue`, `BatterPercentiles.vue`,
`PitcherPercentiles.vue`) only ever looks at the latest rating.

Filed as an epic-tracker ticket, standalone (no other stagged functionality
shares this exact scope, though it overlaps with
[0043](0043-prospect-pipeline.md)'s "development trajectory" — see that
ticket's Design choices for the intended reuse direction).

## 2. Design choices

- **Resolved — what counts as a "meaningful" change.** Flat delta
  thresholds, scoped by rating type: **±5 points** for "overall"
  (current-ability) ratings (`players_batting`, `players_pitching`,
  `players_fielding`, `players_basepath`, `players_fielding_position`), and
  **±10 points** for "talent" (potential/ceiling) ratings
  (`players_batting_talent`, `players_pitching_talent`,
  `players_fielding_position_talent`). Comparison is a **sliding 3-heap
  lookback** — each heap's snapshot compared to the snapshot from 3 heaps
  prior for that player, re-evaluated every heap (not a single
  previous-heap diff, and not a window-average). Grounded in real `ootp`
  data: checked heap-to-heap deltas on `players_batting.contact/power` and
  `players_pitching.stuff` — rating values only move in steps of 5 on this
  scale; ~97% of player/category/heap comparisons show 0 change, ~2.7% show
  a single 5-point move (routine monthly drift, not signal), and 10+-point
  single-heap jumps are rare (~0.01–0.1% of comparisons). See
  [0050](0050-rating-trend-query-layer.md) for the query implementation.
- **Resolved — age-relative-development comparison: out of scope for v1**
  (raw trend only). "Age-relative development" implies comparing a
  player's trajectory against typical aging curves for their age — the same
  age-curve gap flagged in
  [0026](0026-pitcher-projection-methodology.md)'s Design choices
  (age-development is currently skipped entirely in both projection
  classes). Deferred to a future ticket if pursued; not part of 0050–0052.
- **Resolved — actual vs. projected performance tracking: out of scope for
  v1** (ratings-trend only). Ratings snapshots exist per heap, but *actual
  in-game performance* per heap doesn't — `players_career_batting_stats`/
  `players_career_pitching_stats` are year-scoped season totals, not
  per-heap deltas. Deferred to a future ticket if a heap-dated performance
  slice is later built; not part of 0050–0052.
- **Resolved — no new ingestion needed for the ratings-trend half.** Unlike
  every other epic in this batch, the core "track rating changes over time"
  functionality has zero data gaps — it's a read-only aggregation over
  already-ingested snapshots. This makes it the most self-contained of the
  seven stagged functionalities and a reasonable one to prioritize first if
  sequencing across epics is being considered (see
  [0038](0038-gm-command-center.md)'s Outstanding note on build order).

## 3. Approach

Broken down into three sequential sub-tickets, mirroring the layering used
by the pitcher-projection epic (0026/0027/0028):

```
[ ] 0050 Rating delta/trend query layer + API route
      |
      v
[ ] 0051 Development alert generation (narrative rule layer)
      |
      v
[ ] 0052 Frontend trend/alert display (PlayerDetails.vue)

[x] = Closed   [ ] = Open   [~] = In-Progress
```

- [0050](0050-rating-trend-query-layer.md) — the delta/trend query layer:
  new SQL script under `app/db/sql_scripts/api/` plus a route extending
  `app/api/ratings.py`, implementing the sliding 3-heap lookback and
  thresholds resolved above.
- [0051](0051-development-alert-generation.md) — the alert generation rule
  layer: turns 0050's exceeded deltas into the source doc's narrative-style
  alerts.
- [0052](0052-development-monitor-frontend.md) — the frontend trend/alert
  view on the existing player detail page
  (`frontend/src/components/PlayerDetails.vue`), rather than a standalone
  page, since it's inherently player-scoped.
- Output feeds [0043](0043-prospect-pipeline.md)'s "development trajectory"
  need once built (see that ticket's Design choices).

**Files involved:**
- See [0050](0050-rating-trend-query-layer.md), [0051](0051-development-alert-generation.md),
  [0052](0052-development-monitor-frontend.md) for the per-sub-ticket file
  lists.
