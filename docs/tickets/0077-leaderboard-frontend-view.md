# 0077 — Leaderboard frontend view

- **Tag:** feat
- **Status:** Open
- **Depends on:** [0076](0076-leaderboard-query-layer-api.md)
- **Blocks:** —

## 1. Problem

[0076](0076-leaderboard-query-layer-api.md) exposes the leaderboard over
the API; nothing renders it.

## 2. Design choices

Resolved in 0074: a new dedicated view/route, not a mode toggle grafted
onto `ProspectPipeline.vue` — the three-curated-section response shape is
different enough from the org-scoped flat table that it warrants its own
component, same reasoning 0070 used for building a dedicated view rather
than repurposing `TeamDepthChart.vue`.

## 3. Approach

- New view (e.g. `ProspectLeaderboard.vue`) at a new route (e.g.
  `/prospects/leaderboard`), fetching
  `GET /api/prospects?leaderboard=1` (plus `page`/`position`/`level`
  filters as needed).
- Three sections: Top 100 Overall (paginated — page controls), Top 10 by
  Position, Top 10 by Level. Reuses existing display conventions from
  `ProspectPipeline.vue`: the FV badge (with `risk_tag`, ticket 0072),
  `formatMoney`/`formatPercent`, the `mlb_promotion_ready` icon, trend
  badges.
- Linked from `ProspectPipelinePicker.vue` (e.g. a "View league-wide
  leaderboard" link alongside the org picker) and from
  `LandingPage.vue`'s tool card area if warranted.

**Files involved:**
- TBD at implementation time — new Vue view + route registration, exact
  component/layout decisions to match existing frontend conventions
  (same convention 0070/0073 followed).
