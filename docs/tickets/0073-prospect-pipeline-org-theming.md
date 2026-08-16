# 0073 — Org color theming for the Prospect Pipeline page

- **Tag:** feat
- **Status:** Open
- **Depends on:** [0070](0070-prospect-pipeline-frontend.md)
- **Blocks:** —

## 1. Problem

Filed from a user report while reviewing the Prospect Pipeline: selecting
an org on `ProspectPipeline.vue` shows a fixed teal header, unlike
`TeamDepthChart.vue` (ticket 0064), which themes its header with the
selected MLB team's real colors (`teams.background_color`/`text_color`,
applied via a `teamColors` computed + inline CSS custom properties). The
Prospect Pipeline is the same "pick an org, see org-scoped data" shape as
the depth chart and should carry the same theming for visual consistency
between the two Farm-System-adjacent views.

## 2. Design choices

Mostly none — this is expected to be straightforward reuse of 0064's
established pattern, not a new design question. One real implementation
detail worth deciding when this is picked up (not resolved here, since the
user asked only to file the ticket):

- **Outstanding — where the color data comes from.** `GET /api/prospects`
  doesn't return `background_color`/`text_color` (unlike
  `get_org_depth_chart.sql`'s response, which `TeamDepthChart.vue`
  already reads them from). `ProspectPipeline.vue` currently fetches
  `GET /api/teams` separately just to resolve the org's display name --
  that endpoint's `SELECT` (`app/api/teams.py::get_mlb_teams`) already
  reads from `teams`, so adding `background_color`/`text_color` to its
  existing column list is the smallest change (no new endpoint, no
  wasted depth-chart fetch just for two color columns) and is the likely
  right call, but left as an explicit decision for whoever picks this up
  rather than assumed.

## 3. Approach

TBD at implementation time — expected to mirror `TeamDepthChart.vue`'s
`teamColors` computed property and inline `:style` binding almost exactly,
once the color-data-source question above is settled.

**Files involved:**
- `frontend/src/views/ProspectPipeline.vue` (modified)
- `backend/app/api/teams.py` (`get_mlb_teams`, likely modified per the
  Outstanding question above)
- `backend/docs/openai.yaml` (modified, if the `/api/teams` response shape
  changes)
