# 0065 — GM organization selection + app-wide color theming

- **Tag:** feat
- **Status:** Open
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

- **Persistence: `localStorage`, not a backend session/user concept.**
  This app has no auth/login/multi-user concept anywhere today (confirmed:
  no session middleware, no user table). **Outstanding:** confirm
  `localStorage` (survives reloads, scoped to the browser, no backend
  change needed) is the right call rather than a URL param or a new
  backend "current org" endpoint — leaning `localStorage` since it's the
  lowest-friction option and nothing else in the app needs to know a
  user's selected org server-side.
- **Where the selection lives / how it's shared app-wide.** Needs a
  small shared reactive store so any component can read the selected
  `team_id` and its colors without prop-drilling. **Outstanding:** a
  plain reactive `ref`/composable (e.g. `frontend/src/composables/
  useCurrentTeam.ts`, matching this app's existing composition-API style)
  vs. introducing Pinia (not currently a dependency — confirmed via
  `grep` for `pinia` across `frontend/src`, no hits). Leaning composable,
  since the app doesn't need Pinia's fuller feature set (devtools,
  multi-store modules) for one small piece of shared state, and adding a
  new state-management dependency for this alone seems like more than
  this ticket needs.
- **Theming mechanism: reuse 0064's inline CSS-custom-property approach,
  hoisted to `App.vue`.** 0064 already proved out `--team-bg`/`--team-
  text` CSS custom properties set inline per-page; this ticket's job is
  mostly relocating that same mechanism to apply at the app root
  (`App.vue`) instead of one view, driven by the persisted selection
  instead of the currently-viewed team. **Outstanding:** how much of the
  UI actually repaints with team colors (just the header/nav, per the
  literal "GM tab" ask? or every teal accent throughout the app, e.g.
  `SurplusValue.vue`'s recommendation badges, `BatterPercentiles.vue`'s
  section underlines?) — a full reskin of every hardcoded `teal-*`
  Tailwind class across the codebase is a much larger, riskier change
  than just recoloring the header/nav, and not clearly what was asked
  for ("set the UI color scheme to match" is ambiguous on scope). Needs
  a design pass before implementation, not decided here.
- **Contrast/accessibility.** Real MLB team color pairs aren't guaranteed
  to be readable against arbitrary backgrounds (0064 used them only
  against each other — `background_color` behind text colored
  `text_color`, i.e. exactly how OOTP itself pairs them). Applying them
  more broadly (e.g. as accent colors on a white page background) risks
  poor contrast for some teams. **Outstanding:** needs real-data spot
  checks across a sample of teams before broad rollout, not decided here.

## 3. Approach

Not scoped into concrete steps yet — the Outstanding questions above
(state location, theming scope/mechanism, contrast handling) need
resolving first, following this project's established pattern of asking
before assuming design decisions on a ticket like this.

**Files involved:** TBD once the Outstanding questions above are
resolved — likely `frontend/src/components/Header.vue` (new "GM" tab/
selector), a new composable under `frontend/src/composables/`, and
`frontend/src/App.vue` (apply the persisted theme at the app root).
