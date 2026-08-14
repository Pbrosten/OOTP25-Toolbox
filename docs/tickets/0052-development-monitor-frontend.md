# 0052 — Player development monitor: frontend trend/alert display

- **Tag:** feat
- **Status:** Closed
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
- **Resolved — empty/no-history state.** A player with fewer than 4
  recorded heaps (see 0050) returns an empty trend list, not an error. The
  section still renders with an explicit "not enough history yet" message
  rather than being omitted — confirms the feature is working and sets
  expectations, rather than leaving the user wondering if something's
  broken or missing.

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

**Verified:** backend pytest suite (86 passed, unaffected — no backend
changes in this ticket). Confirmed `DevelopmentTrends.vue` and the modified
`PlayerDetails.vue` compile and hot-reload cleanly in the running frontend
container (`vite`'s dev-server logs show clean HMR updates, no errors; both
files serve 200 through Vite's module transform). Ran `npm run build`
(`vue-tsc -b`) in the frontend container and confirmed it does **not**
introduce any new class of error — every `Cannot find module '@/...'`
failure it reports (including one for this ticket's own import) also fires
identically on a `git stash` of this ticket's changes, i.e. the container's
type-check step has a pre-existing, unrelated path-alias resolution
problem affecting every `@/`-aliased import in the app, not something this
ticket caused.

**Not verified — no visual/browser check.** No browser automation tool was
available in this session, so the rendered page (alert callout styling, the
collapsed-by-default `<details>` grouping, the empty-state message) was not
visually confirmed, only compiled/served successfully. Recommend a manual
check of `/player/<id>` before closing — e.g. player_id 6 (MLB position
player: overall babip/power/eye + speed/defense) or player_id 12 (non-MLB
position player: talent babip/power/eye, still-overall speed/defense) from
0050's Amendment testing.

**Files involved:**
- `frontend/src/components/DevelopmentTrends.vue` (new)
- `frontend/src/components/PlayerDetails.vue` (modified)

## 4. Amendment — display trimmed to 0050's restricted category set

See [0050](0050-rating-trend-query-layer.md)'s Amendment section for the
full scope change. `DevelopmentTrends.vue`'s `tableLabels` map dropped its
`players_fielding_position`/`players_fielding_position_talent` entries
(that table is no longer queried at all — defense is now 3 named
`players_fielding` columns, not per-position grades), and `getColumnLabel`
lost its position-code special-casing (`pos1`.."pos9" -> `P`.."RF")
accordingly, keeping only a `babip` -> `BABIP` override on top of the
generic snake_case formatter. No structural change to the component's
fetch/grouping/empty-state logic — it already grouped generically by
whatever `table_name`s the API returned. Re-verified via the live routes
(not a browser check, same limitation as above) that a pitcher's `/trends`
response now only produces a "Pitching" `<details>` group, not "Batting".

## 5. Amendment — notifications only, delta breakdown removed

Requested directly: display only the alert callouts, drop the per-category
delta breakdown entirely (the grouped `<details>`/table UI from the
Amendment above). `DevelopmentTrends.vue`'s `tableLabels`, `getColumnLabel`,
and `groupedTrends` are gone along with the `<details>` markup — none of
that is reachable from the template anymore. The component still fetches
`/trends` (not just `/trends/alerts`), but only reads `trends.length` from
it now, to keep the existing "not enough history yet" vs. "no notable
changes" distinction (both cases return an empty alerts list, so that
split still needs 0050's row count, not just 0051's). No backend changes —
this is a display-only revision to what 0052 already resolved as "what
renders" in its Design choices section above (that resolution is
superseded: it's alerts only now, not alerts + delta view).
