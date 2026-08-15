# 0061 — Refetch player data when navigating between player pages

- **Tag:** fix
- **Status:** Closed
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
- `frontend/src/components/PlayerDetails.vue` (modified — batting/pitching
  fetches gated on known position, see correction below)

**Verified:** `<router-view :key="$route.fullPath" />` compiles and hot-
reloads cleanly (Vite HMR, no errors); `npx vue-tsc -b` reports the same 32
pre-existing type errors with and without this change, none attributable
to this one-line edit. **Not verified in an actual browser** at the time —
this environment has no browser-automation tool available, and reproducing
the original bug specifically requires a client-side SPA navigation between
two `/players/:id` history entries.

## Post-implementation correction: the diagnosis above was incomplete

User re-tested and reported the problem persists — screenshot showed a
**fresh, full page load** of Yamamoto's page (network panel: 54-request
initial load, `DOMContentLoaded`, not a client-side transition) still
displaying a red "Failed to load batting stats." banner under the pitching
table. This is not the stale-navigation case the `:key` fix addresses —
it's a plain, deterministic bug on every direct/fresh visit to any pure
pitcher's page, which the original investigation's own curl check
(`GET /api/players/36289/career/batting` → 404) had actually already
surfaced but mis-classified as "correctly empty" without checking how the
frontend *handles* that 404.

**Actual primary root cause:** `PlayerDetails.vue`'s `onMounted` (pre-fix,
lines 15-67) fetched `/career/batting` unconditionally for every player —
in parallel with `/details`, before position was even known — and on any
non-OK response (including the legitimate 404 every pure pitcher's
`career/batting` endpoint returns, since he has zero
`players_career_batting_stats` rows) set the single shared `error` ref to
`'Failed to load batting stats.'`, rendered unconditionally at the
template's `v-if="error"` banner (line 388, no position gate). This fires
on **every** pure pitcher's page, every load — not an edge case. The
template's own batting/pitching table `v-if`s (`position !== 'P'` /
`=== 'P'`) were and are correct; only the fetch-and-error-reporting logic
above them was unconditional.

**Fixed:** restructured `onMounted` to fetch `/details` first (no longer
parallelized with the batting fetch, since position must be known before
deciding what else to fetch — same dependency the pitching fetch already
had), then only fetch/report-on `/career/batting` when
`playerDetails.value?.position !== 'P'`, mirroring the template's existing
gate. Added the same guard symmetrically to the pitching fetch's error
case (previously silent on failure, now sets `'Failed to load pitching
stats.'` consistent with the batting path) since both fetches are now
structured identically. The `<router-view :key>` fix from the original
diagnosis is kept — the stale-navigation issue it addresses is real and
independently confirmed (no data-fetching component in the player-page
tree watches `props.playerId`), just not what this particular screenshot
was showing.

**Re-verified** against the live dev stack: `GET
/api/players/36289/details` → `position: "P"`; `GET
/api/players/36289/career/pitching` → `200`; `GET
/api/players/36289/career/batting` → still `404` as expected, but the
frontend no longer issues this request at all for a pitcher (confirmed via
the updated `onMounted` logic), so no error banner fires. Vite HMR
recompiled `PlayerDetails.vue` cleanly; `npx vue-tsc -b` still reports the
same 32 pre-existing type errors, none new. **Still not verified visually
in an actual browser** — same tooling limitation as before. Please
manually confirm: a fresh load of `/players/36289` shows no "Failed to
load batting stats." banner, a fresh load of a batter's page (e.g. Ohtani,
33695) shows no equivalent pitching-stats error, and the client-side
navigation scenario from the original diagnosis is also clean.
