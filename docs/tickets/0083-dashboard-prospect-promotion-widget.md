# 0083 — Command Center: prospect promotion opportunities widget

- **Tag:** feat
- **Status:** Open
- **Depends on:** —
- **Blocks:** [0085](0085-gm-command-center-dashboard.md)

## 1. Problem

[0038](0038-gm-command-center.md) calls for surfacing prospects who are
ready for MLB promotion. This is already fully wired:
`GET /api/prospects?team_id=&level=` (from
[0068](0068-prospect-fv-value-calculation.md)/[0069](0069-prospect-query-layer-api.md))
returns an `mlb_promotion_ready` flag per prospect. This ticket is
frontend-only — no new backend work needed.

## 2. Design choices

Reuse the existing endpoint as-is, filtering for `mlb_promotion_ready ===
true`. No real alternatives considered — the data and flag already exist
in exactly the shape this widget needs.

## 3. Approach

Frontend widget calling `GET /api/prospects?team_id=<currentTeamId>`,
filtering to `mlb_promotion_ready` prospects, rendering them similarly to
`ProspectPipeline.vue`'s existing promotion-ready badge
(`ArrowUpCircleIcon`), linking each to the player's profile.

**Files involved:**
- `frontend/src/components/dashboard/PromotionReadyWidget.vue` (new).
