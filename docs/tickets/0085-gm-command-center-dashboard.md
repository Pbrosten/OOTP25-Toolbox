# 0085 — GM Command Center dashboard shell

- **Tag:** feat
- **Status:** Closed
- **Depends on:** [0079](0079-dashboard-team-war-widget.md), [0080](0080-dashboard-over-underperformers-widget.md), [0081](0081-dashboard-roster-weaknesses-widget.md), [0082](0082-dashboard-contract-arbitration-widget.md), [0083](0083-dashboard-prospect-promotion-widget.md), [0084](0084-dashboard-action-queue.md)
- **Blocks:** —

## 1. Problem

[0038](0038-gm-command-center.md) (GM Command Center) calls for a single
landing dashboard scoped to the GM's org. Today `LandingPage.vue` is a
bare `ToolCard` launcher with no team/roster content. This ticket wires
the widgets from 0079–0084 into that dashboard.

## 2. Design choices

- **Placement: replace the Home page vs. a new separate route.** Resolved
  with the user 2026-08-16: **replace `LandingPage.vue`**. Matches the
  source doc's top-level position for the Command Center, and avoids a
  redundant landing page now that [0065](0065-gm-org-selection-theming.md)'s
  `Sidebar.vue` already carries the tool launcher/nav — a separate
  `/dashboard` route would just be a second home.
- **Build order: shell-with-placeholders vs. build after 0079–0084 land.**
  Originally chosen: build this last, after 0079–0084 all ship. **Revised
  by the user 2026-08-23**: build the shell now, as a work-in-progress
  page, and drop each of 0079–0084's widgets in as its own ticket closes.
  This page doubles as the visual-confirmation surface for those tickets
  while they're still in progress, rather than only becoming visible once
  the whole epic lands.
- **"Current team" scoping.** Resolved by
  [0065](0065-gm-org-selection-theming.md) — `useCurrentTeam()` already
  provides `currentTeamId`/`currentTeam`.
- **No-org-selected state.** Resolved 2026-08-23: a prompt directing to
  `/gm`, not a fallback to the old `ToolCard` launcher — `Sidebar.vue`
  already covers that nav (see Placement above), so falling back to it
  would just reintroduce the redundancy this ticket removes. `ToolCard.vue`
  is now unused and deleted.

## 3. Approach

Built incrementally as a work-in-progress shell (see Design choices'
revised build order), each of 0080–0084 dropping its own widget in as it
closed — this section describes the final shape now that all of
0079–0084 are closed.

`LandingPage.vue` replaces the old `ToolCard` launcher with: a header
strip (0079's `TeamWarWidget`, the team power ranking), a "Roster
Insights" section stacking 0081/0082/0080's widgets
(`RosterWeaknessesWidget`/`ContractDecisionsWidget`/
`PerformanceDeltasWidget`, each full-width — their internal multi-item
list layouts don't fit a compact stat-tile grid cell), and a "Prospect
Watch" section for 0083's `PromotionReadyWidget`. All scoped by
`useCurrentTeam().currentTeamId`, with a no-org-selected prompt to `/gm`.

0084's `ActionQueue` ended up as a collapsible feed to the right of that
main content (a `flex` row, stacking on small screens), not a third
full-width section under it — a layout revision made after this ticket's
original placeholder-section draft; see 0084's own ticket for the
collapse-toggle/layout detail. `useActionQueue()`'s shared alert registry
is how the sibling widgets feed it without `LandingPage.vue` having to
orchestrate any prop-passing between them.

**Files involved:**
- `frontend/src/views/LandingPage.vue` (modified — dashboard shell;
  final two-column layout, all widgets wired in).
- `frontend/src/components/ToolCard.vue` (deleted — no longer used once
  the old tool-launcher grid is replaced; `Sidebar.vue` already covers
  that nav).
- `frontend/src/router/index.ts` — unchanged; route path stays `/`.
