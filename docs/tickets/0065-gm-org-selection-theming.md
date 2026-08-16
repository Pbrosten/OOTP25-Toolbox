# 0065 — GM organization selection + app-wide color theming

- **Tag:** feat
- **Status:** Closed
- **Depends on:** —
- **Blocks:** —

## 1. Problem

Reported directly while reviewing [0064](0064-roster-depth-chart-frontend.md)'s
depth-chart page: it now themes itself with the *viewed* org's real MLB
colors (`teams.background_color`/`text_color`), scoped to that one page
only. The ask is broader — a persistent "this is my org" selection,
surfaced as a new tab in the app header, that themes the **whole app**
to match, not just one page.

This is the same "no current-team/session concept exists anywhere in the
app" gap [0038](0038-gm-command-center.md) (GM Command Center) already
flagged as an unresolved Outstanding question, and
[0039](0039-roster-optimization-org-depth.md) (Roster Optimization) also
sidestepped by requiring an explicit `team_id` in the URL rather than
inferring one. This ticket resolves that gap directly, narrowly scoped to
"select an org + theme the UI" — not the full GM Command Center dashboard
itself (0038 remains its own ticket, and can consume whatever this ticket
lands, e.g. a `useCurrentTeam()`-style composable, once it exists).

## 2. Design choices

Resolved with the user 2026-08-16:

- **Persistence: `localStorage`.** No auth/login/multi-user concept
  exists anywhere in this app today (confirmed: no session middleware,
  no user table). The selected org's `team_id` persists in
  `localStorage`, survives reloads, scoped to the browser. No backend
  change needed.
- **State sharing: plain composable, not Pinia.** A new
  `frontend/src/composables/useCurrentTeam.ts` exposing a reactive
  selected-team ref (backed by the `localStorage` value), matching this
  app's existing composition-API style. Pinia is not a dependency today
  and isn't needed for one piece of shared state.
- **Theming scope: full reskin.** Every hardcoded `teal-*` Tailwind
  accent across the app (badges, underlines, buttons, borders, etc.) is
  replaced with the selected org's team colors, not just the header/nav.
  This is the larger/riskier option flagged in the original ticket, but
  is what was chosen.
- **Theming mechanism: reuse 0064's inline CSS-custom-property approach,
  hoisted to `App.vue`.** 0064 already proved out `--team-bg`/`--team-
  text` CSS custom properties set inline per-page. This ticket relocates
  that mechanism to the app root (`App.vue`), driven by the persisted
  `useCurrentTeam()` selection instead of the currently-viewed team, and
  the reskinned components consume the same CSS variables instead of
  hardcoded `teal-*` classes.
- **Contrast/accessibility: use colors as-is.** Same pairing 0064 (and
  OOTP itself) uses — `background_color` behind text colored
  `text_color`. No contrast-ratio fallback logic. Revisit only if a real
  team's pair turns out to look bad in practice.

## 3. Approach

Implemented 2026-08-16:

1. `frontend/src/api/teams.ts` (new) — typed `fetchTeams()` client for
   `GET /api/teams` (no lightweight single-team route exists; the
   composable fetches the full list once and finds the current team
   client-side, matching the pattern `ProspectPipeline.vue` already used).
2. `frontend/src/composables/useCurrentTeam.ts` (new) — module-level
   singleton reactive state: `currentTeamId` backed by `localStorage`
   (`ootp-toolbox:current-team-id`), `currentTeam` derived from the
   fetched list, `teamColors` computed (`--team-bg`/`--team-text`, falling
   back to the app's original teal-800/white when no org is selected),
   and `setCurrentTeam(id)`.
3. `frontend/src/views/GmOrgSelect.vue` (new) + `/gm` route
   (`frontend/src/router/index.ts`) — the "GM" tab's destination, styled
   as a settings/configuration panel rather than a picker list: a "My
   Organization" field with a `<select>` dropdown (plus color swatch)
   bound to `useCurrentTeam()`.
4. `frontend/src/components/Header.vue` — added nav links for "Depth
   Chart" (`/teams`, the existing `TeamPicker.vue` route) and "Prospect
   Pipelines" (`/prospects`, the existing `ProspectPipelinePicker.vue`
   route) alongside the new "GM" tab — both tools existed already but
   weren't reachable from the header nav. The header itself now themes
   via `bg-team`/`text-team-on-bg` instead of the old hardcoded
   `bg-teal-800 text-white`.
5. `frontend/src/App.vue` — wraps `<Header/>` + `<router-view/>` in a div
   with `:style="teamColors"` from `useCurrentTeam()`, so the CSS custom
   properties cascade to every page.
6. `frontend/src/style.css` — new `.bg-team`/`.text-team`/
   `.text-team-on-bg`/`.border-team`/`.bg-team-subtle` (light tint via
   `color-mix()`) utility classes, replacing the old static `teal-*`
   Tailwind classes app-wide (13 files, ~45 occurrences swept).
   `TeamDepthChart.vue`/`ProspectPipeline.vue` keep their own local
   `teamColors` override (0064) for the *viewed* team's colors — CSS
   custom property scoping means `var(--team-bg)` inside those pages'
   already-existing wrapper div resolves to the viewed team, while every
   other page (and the header/nav) resolves to the app-root "my org"
   value from `useCurrentTeam()`. No conflict between the two concepts.
7. `frontend/src/views/TeamPicker.vue` (`/teams`) and
   `ProspectPipelinePicker.vue` (`/prospects`) — both source their team
   list from `useCurrentTeam()` instead of their own `fetch('/api/
   teams')`, keeping a single shared fetch/error state
   (`useCurrentTeam()` gained a `teamsError` ref for this). Both remain
   plain manual pickers — an auto-select-and-navigate-to-the-GM's-own-org
   behavior was tried and then explicitly removed, since selecting an
   org for these two tools should stay a deliberate per-visit choice, not
   implied by the separate app-wide "My Organization" theming selection.
8. `frontend/src/views/LandingPage.vue` — the Home page's "Roster Depth
   Chart" and "Prospect Pipeline" tool cards route to `/teams` and
   `/prospects` respectively — each tool's own org-selection page (step
   7's picker views), not the shared `/gm` settings screen.
9. `frontend/src/components/Sidebar.vue` (new) — the per-tool links
   ("Find a Player", "Depth Chart", "Prospect Pipelines") moved out of
   `Header.vue`'s top bar into a left sidebar. `Header.vue`'s top nav now
   only has "Home" and "GM". `App.vue` lays out `<Header/>` on top, then
   a flex row of `<Sidebar/>` + `<main><router-view/></main>` below it.
   Sidebar visuals: a "TOOLS" section label, a `@heroicons/vue/24/outline`
   icon per link (`MagnifyingGlassIcon`/`UserGroupIcon`/
   `RocketLaunchIcon`), hover state (white pill + team-colored text), and
   an active-route state (`bg-team-subtle`/`text-team` via `router-link`'s
   `active-class`) instead of the original plain stacked text links.

**Files involved:** `frontend/src/api/teams.ts` (new),
`frontend/src/composables/useCurrentTeam.ts` (new),
`frontend/src/views/GmOrgSelect.vue` (new),
`frontend/src/router/index.ts`, `frontend/src/components/Header.vue`,
`frontend/src/App.vue`, `frontend/src/style.css`, and every component
that previously used hardcoded `teal-*` classes: `DevelopmentTrends.vue`,
`PlayerDetails.vue`, `SurplusValue.vue`, `BatterPercentiles.vue`,
`PercentileBar.vue`, `PitcherPercentiles.vue`, `PlayerProfile.vue`,
`PlayerSearch.vue`, `ProspectLeaderboard.vue`, `ProspectPipeline.vue`,
`ProspectPipelinePicker.vue`, `TeamDepthChart.vue`, `TeamPicker.vue`.

**Verification:** `npm run build`'s `vue-tsc -b` errors are pre-existing
(confirmed identical on `develop` before this change — the container's
tsc invocation doesn't resolve `@/` path aliases at all, unrelated to
this ticket). Dev server HMR picked up every change cleanly, `/gm` route
returns 200, and `GET /api/teams` confirmed returning real
`background_color`/`text_color` per team. Not verified in an actual
browser (no browser tool available this session) — worth a manual
visual pass before closing.
