# 0083 — Command Center: prospect promotion opportunities widget

- **Tag:** feat
- **Status:** Closed
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

`frontend/src/api/prospects.ts` (new, no such module existed yet --
other prospect-related views fetch inline) adds `fetchTeamProspects`,
typed to just the fields this widget needs (`value.available`/
`value.fv`/`value.mlb_promotion_ready`, not the full row shape
`ProspectPipeline.vue` renders). `PromotionReadyWidget.vue` calls it with
`useCurrentTeam().currentTeamId`, filters to `value.available &&
value.mlb_promotion_ready`, sorts by FV descending, and renders each
with the same `ArrowUpCircleIcon` badge/tooltip and FV-tier coloring
(`fvClass`) as `ProspectPipeline.vue`'s table, linking to the player's
profile page. Scoping via `team_id` already includes every affiliate
(existing endpoint behavior), so no additional level filtering is
needed beyond the flag itself. Wired into `LandingPage.vue` (ticket
0085) under its own "Prospect Watch" section heading, separate from
0081/0082's "Roster Insights" section (per the user, 2026-08-23).

**Files involved:**
- `frontend/src/api/prospects.ts` (new) — `fetchTeamProspects` +
  `Prospect`/`ProspectValue` types.
- `frontend/src/components/dashboard/PromotionReadyWidget.vue` (new).
- `frontend/src/views/LandingPage.vue` (modified) — widget wired into
  the dashboard shell's own "Prospect Watch" section.
