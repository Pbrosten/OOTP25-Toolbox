# 0052 — Player development monitor: frontend trend/alert display

- **Tag:** feat
- **Status:** Open
- **Depends on:** [0050](0050-rating-trend-query-layer.md), [0051](0051-development-alert-generation.md)
- **Blocks:** —

## 1. Problem

[0050](0050-rating-trend-query-layer.md) and
[0051](0051-development-alert-generation.md) expose raw deltas and narrative
alerts over the API, but nothing renders them. [0044](0044-player-development-monitor.md)'s
Approach section calls for this to live on the existing player detail page
rather than a standalone view, since it's inherently player-scoped.

## 2. Design choices

- **Resolved — placement.** A new section within
  `frontend/src/components/PlayerDetails.vue` (or a new child component it
  mounts), alongside the existing career-stats tables, rather than a
  standalone route — matches 0044's stated approach and how
  `BatterPercentiles.vue`/`PitcherPercentiles.vue` are already mounted
  per-player rather than as their own pages.
- **Resolved — what renders.** Two pieces, both scoped to the current
  player: (1) any active alerts from 0051, rendered as short text
  callouts/badges; (2) a per-category delta view from 0050's full trend
  list (not just exceeded ones) so a user can see the 3-heap trend even
  when nothing crossed threshold. Given the volume of rating columns (8
  tables), the delta view groups by table (Batting, Pitching, Fielding,
  Basepath, and their Talent counterparts) collapsed by default, consistent
  with how `PlayerDetails.vue`'s existing career tables are already
  sectioned.
- **Outstanding — empty/no-history state.** A player with fewer than 4
  recorded heaps (see 0050) returns an empty trend list, not an error. What
  renders in that case (nothing, or an explicit "not enough history yet"
  message) is a small UX call — flagging rather than deciding here, ask
  when this ticket is picked up.

## 3. Approach

- New component `frontend/src/components/DevelopmentTrends.vue`: fetches
  `/api/players/ratings/<playerId>/trends` and
  `/api/players/ratings/<playerId>/trends/alerts` (or whatever 0051 settles
  its route name to), renders alert callouts followed by the grouped
  per-table delta breakdown.
- `frontend/src/components/PlayerDetails.vue`: mounts `DevelopmentTrends`
  alongside the existing batting/pitching career tables, passing
  `props.playerId` through (same prop it already receives).
- `backend/docs/openai.yaml`: no backend change here, just confirms the
  routes this component depends on are documented (done in 0050/0051).

**Files involved:**
- `frontend/src/components/DevelopmentTrends.vue` (new)
- `frontend/src/components/PlayerDetails.vue` (modified)
