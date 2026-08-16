# 0070 — Prospect Pipeline frontend view

- **Tag:** feat
- **Status:** Open
- **Depends on:** [0069](0069-prospect-query-layer-api.md)
- **Blocks:** —

## 1. Problem

[0069](0069-prospect-query-layer-api.md) exposes the prospect data over the
API; nothing renders it. `docs/improvements/expanded-functionality.md`
suggests a `FARM SYSTEM › Prospect Pipeline` IA placement — this ticket is
that view, mirroring how [0064](0064-roster-depth-chart-frontend.md) built
the org depth-chart view on top of 0063's API.

## 2. Design choices

No new design questions beyond what 0043 already resolved — this is
presentation of already-defined data (FV grade, surplus value, star odds,
MLB-promotion-ready flag, trend direction). Layout/component-structure
choices deferred to implementation time, same as 0064's approach.

## 3. Approach

- New route/view under the Farm System IA area, listing prospects
  filterable by org/level/position, sortable by FV grade or surplus value.
- Reuse existing display conventions: 20-80 grade bars
  (`PercentileBar.vue`-adjacent components already used elsewhere for
  20-80 scale display), trend indicators from 0052's
  `DevelopmentTrends`-style display, and 0057's surplus-value display
  conventions for the dollar figures.
- Promotion-ready prospects surfaced distinctly (matches the source doc's
  "surfacing prospects ready for promotion" ask).

**Files involved:**
- TBD at implementation time — new Vue view + route registration, exact
  component names to match existing frontend conventions.
