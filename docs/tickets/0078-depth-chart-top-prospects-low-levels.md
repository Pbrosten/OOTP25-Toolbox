# 0078 — Top-10 prospect rankings at A/High-A and Rookie/Complex on the Org Depth Chart

- **Tag:** feat
- **Status:** Closed
- **Depends on:** [0064](0064-roster-depth-chart-frontend.md), [0069](0069-prospect-query-layer-api.md)
- **Blocks:** —

## 1. Problem

[0064](0064-roster-depth-chart-frontend.md) deliberately left levels 4/6
(A/High-A, Rookie/Complex) as plain roster-count tiles on the Org Depth
Chart, not WAR-ranked player lists like MLB/AAA/AA get — at the time,
`BatterProjection`/`PitcherProjection` only had a current-ratings WAR
signal, which the user agreed "isn't a meaningful ranking signal that far
from MLB-readiness," and building a real talent-based alternative would
have meant "a whole parallel projection methodology" (0064's Design
choices, resolved as out of scope then).

That talent-based methodology now exists: ticket 0068's FV/surplus-value
calc is specifically a talent-*ceiling* projection (not current-form WAR),
exactly the missing signal 0064 flagged, and it's already computed and
exposed per-org via `GET /api/prospects?team_id=...` (0069). The user
wants the depth chart's A/High-A and Rookie/Complex tiles to gain a real
top-10 ranking using it.

## 2. Design choices

Resolved via a direct design conversation with the user:

- **Resolved — show both.** The existing per-position roster-count tiles
  stay as-is at levels 4/6; a new "Top 10 Prospects" list is added below
  them, not a replacement.
- **Resolved — one combined top-10 per level, not per position.** A
  single ranked list of the org's 10 best prospects at that level overall
  (by `fv` descending, `surplus_value` descending as tiebreak) — not
  broken out by position like the WAR-ranked levels (1/2/3) are.
- **Resolved (not asked directly, low-stakes) — data source: reuse
  `GET /api/prospects` as-is, no backend changes.** The existing
  org-scoped, live-computed endpoint (0069) already returns exactly this
  data; `TeamDepthChart.vue` fetches it once (unfiltered by level, in
  parallel with the existing depth-chart fetch) and computes the
  per-level top-10 client-side, the same way `ProspectPipeline.vue`
  already sorts its own fetch client-side. One extra request total, not
  two (one per level) — cheaper and simpler.
- **Resolved (not asked directly, low-stakes) — display richness: match
  `ProspectPipeline.vue`'s FV badge/risk-tag, not the depth chart's plain
  WAR number.** Reusing the established FV-badge convention (tiered
  color, `risk_tag` suffix) reads more clearly for a 20-80 grade than
  forcing it through `warClass`'s WAR-shaped (positive/negative) styling,
  and keeps one visual language for FV across the whole app rather than
  inventing a second one here.

## 3. Approach

- `frontend/src/views/TeamDepthChart.vue`:
  - `fetchDepthChart()` now fetches `GET /api/prospects?team_id=${id}` in
    parallel with the existing depth-chart fetch.
  - New `topProspectsByLevel` computed: filters `prospects` to each
    `COUNT_ONLY_LEVELS` value (4, 6), sorts by `fv` desc /
    `surplus_value` desc, slices the top 10.
  - Template: the `COUNT_ONLY_LEVELS` branch (previously a single `<div>`
    of count tiles) is now a `<template v-if>` wrapping the existing
    count-tile grid plus a new "Top 10 Prospects" table below it — rank,
    name (linked, with the `ArrowUpCircleIcon` `mlb_promotion_ready`
    marker reused from the WAR-ranked levels), position, and an FV badge
    (`fvClass`/`riskTagTitle`, both reused verbatim from
    `ProspectPipeline.vue`).
- No backend changes — `GET /api/prospects` already provided everything
  needed.

**Verified against real data**: `GET /api/prospects?team_id=9` (Colorado)
— level 4 (A/High-A): 21 available prospects, top 5 led by Chris Flores
(FV 70, "-"); level 6 (Rookie/Complex): 29 available prospects, top 5 led
by Andrew Costello/Brad Schmidt/David Burstein (FV 55, "-"). Sort matches
the frontend's own `topProspectsByLevel` key exactly. `TeamDepthChart.vue`
compiles cleanly through Vite's SFC transform. No browser tool available
this session (same disclosed gap as prior frontend tickets) to visually
confirm rendering.

**Files involved:**
- `frontend/src/views/TeamDepthChart.vue` (modified)
