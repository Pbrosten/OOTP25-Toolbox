# 0061 — Refetch player data when navigating between player pages

- **Tag:** fix
- **Status:** Open
- **Depends on:** —
- **Blocks:** —

## 1. Problem

Reported directly: Yoshinobu Yamamoto's player page
(`http://localhost:5173/players/36289`, a pitcher) renders batting stats,
which shouldn't be possible for a pitcher.

Investigated and confirmed **not** a backend or position-check bug —
`players.position` for 36289 is correctly `'P'`,
`players_career_batting_stats` has zero rows for him,
`GET /api/players/36289/details` correctly returns `position: "P"`, and
`GET /api/players/36289/career/batting` correctly 404s. Every
position-gating check in the frontend (`PlayerDetails.vue`'s batting/
pitching table `v-if`s, `PlayerProfile.vue`'s `PitcherPercentiles` vs.
`BatterPercentiles` selector) is individually correct.

**Actual root cause: stale component state from client-side route-param
navigation.** `App.vue`'s `<router-view />` has no `:key` binding, and the
`/players/:id` route reuses the same mounted `PlayerProfile`/
`PlayerDetails`/percentile component instances across navigations between
different player IDs rather than remounting. None of the data-fetching
components refetch when `playerId` changes — `PlayerDetails.vue`,
`BatterPercentiles.vue`, `PitcherPercentiles.vue`, `PitchRepertoire.vue`,
`SurplusValue.vue`, and `DevelopmentTrends.vue` all fetch exclusively inside
`onMounted`, with no `watch(() => props.playerId, ...)`. So navigating
client-side directly from one player's page to another's (e.g. via browser
back/forward across two `/players/:id` history entries, without an
intervening `/search` mount) updates the URL and route params but leaves
the previously-loaded player's name, tables, and percentile bars on screen
under the new URL — exactly matching "Yamamoto's page shows batting stats"
if the previously-viewed player was a batter. A genuine fresh load of
`/players/36289` renders correctly, which is why this wasn't caught by
per-component logic review alone.

## 2. Design choices

- **Fix scope: force a remount via `<router-view :key>`, not per-component
  watchers.** Options considered — (a) add `:key="$route.params.id"` (or
  `$route.fullPath`) to `App.vue`'s `<router-view />`, forcing Vue Router to
  destroy and remount the whole player-page component tree on every
  player-id change; (b) add a `watch(() => props.playerId, ...)` refetch to
  each of the six affected components individually. **Chosen: (a).** Every
  data-fetching component under `/players/:id` shares the same bug (fetch
  only in `onMounted`), so a per-component watcher fix means finding and
  correctly reproducing the same pattern six times today and again for any
  future component added to the player page — a single `:key` at the route
  boundary fixes all of them at once and matches how a fresh page load
  (which behaves correctly today) already works, with no risk of a seventh
  component being missed later. The tradeoff is a full remount (brief
  unmount/remount of the whole page, all six components refetch from
  scratch) rather than (b)'s more surgical in-place data swap — accepted,
  since this is a full-page navigation to begin with (no shared state or
  transition animation between player pages to preserve) and correctness
  across the whole page matters more than avoiding a remount here.
- **Outstanding:** none — `App.vue`'s `<router-view />` is the only mount
  point for `/players/:id`, so there's no risk of the fix missing a
  parallel render path.

## 3. Approach

- `frontend/src/App.vue`: add `:key="$route.fullPath"` to `<router-view />`
  (line 13), forcing a full remount of the routed component tree whenever
  the URL — including the `:id` param — changes.
- Verify manually against the running dev stack (`npm run dev`): navigate
  from a batter's page (e.g. Ohtani, 33695) to Yamamoto's page (36289) via
  client-side navigation that previously reproduced the bug (browser back/
  forward across two player-page history entries), and confirm the page
  correctly shows pitcher-only content immediately, with no stale batting
  table/percentiles flash-then-correct or stuck-stale state. Also confirm
  forward/backward browser navigation between several players in a row
  stays correct, and that a normal search-result click still works
  (already correct today, shouldn't regress).

**Files involved:**
- `frontend/src/App.vue` (modified — `<router-view :key>`)
