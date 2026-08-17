# 0085 — GM Command Center dashboard shell

- **Tag:** feat
- **Status:** Open
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
  0038 flagged this as unresolved when it was blocked on 0039/0042/0043;
  now that those are closed and 0079–0084 are the actual remaining
  dependencies, chosen: **build this last**, after 0079–0084 all ship,
  composing their finished widgets directly — simpler than maintaining a
  partially-broken landing page mid-epic with placeholder sections.
- **"Current team" scoping.** Resolved by
  [0065](0065-gm-org-selection-theming.md) — `useCurrentTeam()` already
  provides `currentTeamId`/`currentTeam`.
- **Outstanding: no-org-selected state.** If `useCurrentTeam().
  currentTeamId` is null (GM hasn't picked an org via `/gm` yet), what the
  dashboard shows instead isn't decided here — likely a prompt directing
  to `/gm`, or falling back to the old `ToolCard` launcher, but needs its
  own call at implementation time.

## 3. Approach

Rework `LandingPage.vue` into a dashboard layout: header/summary strip
(0079's team WAR), 0080/0081/0082/0083's widgets in a grid, and 0084's
Action Queue. All scoped by `useCurrentTeam().currentTeamId`. Depends on
0079–0084 all being complete first (see Design choices above).

**Files involved:**
- `frontend/src/views/LandingPage.vue` (modified — becomes the dashboard).
- `frontend/src/router/index.ts` (modified, if the route path changes).
