# 0084 — Command Center: Action Queue

- **Tag:** feat
- **Status:** Closed
- **Depends on:** [0079](0079-dashboard-team-war-widget.md), [0080](0080-dashboard-over-underperformers-widget.md), [0081](0081-dashboard-roster-weaknesses-widget.md), [0082](0082-dashboard-contract-arbitration-widget.md), [0083](0083-dashboard-prospect-promotion-widget.md)
- **Blocks:** [0085](0085-gm-command-center-dashboard.md)

## 1. Problem

[0038](0038-gm-command-center.md)'s source doc calls for a prioritized
"Action Queue" — a single list summarizing what needs the GM's attention
right now, each with a "why" that links back to the page that explains it
(source doc's Cross-Cutting Design Principle #4). 0038 itself flagged this
as unresolved: whether it needs real cross-widget priority/urgency scoring,
or whether a flat list grouped by category suffices for v1.

## 2. Design choices

- **Flat list grouped by category vs. real cross-widget priority/urgency
  scoring.** Resolved with the user 2026-08-16: **flat list grouped by
  category** for v1. Each contributing widget
  ([0079](0079-dashboard-team-war-widget.md)–[0083](0083-dashboard-prospect-promotion-widget.md))
  is responsible for exposing its own alert-shaped items; this ticket
  just renders them grouped/labeled by source (e.g. "Contract",
  "Prospects", "Roster"), with no cross-category ranking. A real
  priority/urgency scoring function is explicitly deferred — not clearly
  needed for v1 per 0038's own note, and premature before real usage
  shows what actually needs prioritizing.

## 3. Approach

**Collection mechanism.** The sibling widgets are independent, self-
fetching siblings on `LandingPage.vue` with no parent-child relationship
to `ActionQueue.vue` — prop-drilling alerts up through `LandingPage.vue`
and back down would mean it orchestrating state for five widgets it
otherwise doesn't touch. Instead: `frontend/src/composables/
useActionQueue.ts` (new), a module-level singleton reactive `Map<source,
alert[]>` exactly matching `useCurrentTeam.ts`'s existing pattern. Each
of 0080–0083's widgets calls `setAlerts(source, [...])` inside its own
fetch cycle — clearing to `[]` first (so a team switch doesn't show
stale alerts while the new team's data loads), then populating once its
data arrives. `ActionQueue.vue` just reads the aggregated `alerts`
computed, groups by `category`, and renders — no coupling to which
widgets exist or how many there are.

**What counts as an alert, per widget** (0079 contributes nothing — see
Problem/original Approach for why):
- 0080 (`PerformanceDeltasWidget`): every returned player, both
  directions — an overperformer is a buy-low-extend opportunity, an
  underperformer a concern worth watching. Category "Performance".
- 0081 (`RosterWeaknessesWidget`): weaknesses only, not surpluses — a
  surplus is depth, not something needing the GM's attention. Category
  "Roster"; links to the thin position's best player, or the team's
  depth chart if nobody's rostered there at all.
- 0082 (`ContractDecisionsWidget`): every returned player — the backend
  already filters to players with a live recommendation, so all of them
  are actionable. Category "Contract".
- 0083 (`PromotionReadyWidget`): every promotion-ready prospect.
  Category "Prospects".

**Layout, revised by the user 2026-08-23**: not a full-width section
under Roster Insights/Prospect Watch — a collapsible feed to their right
instead. `ActionQueue.vue` owns its own header and collapse toggle
(`collapsed` ref, same `ChevronDoubleLeft/RightIcon` convention as
`Sidebar.vue`, mirrored since this panel is right-docked instead of
left-docked) rather than `LandingPage.vue` wrapping it in a `<section>`,
since the collapsed rail needs to control its own width including the
header. Collapsed state shows just a count badge. `LandingPage.vue`
wraps Roster Insights + Prospect Watch in a `flex-1` column alongside
`<ActionQueue />` in a `flex` row (stacking on small screens). The
internal category grid also changed from a horizontal `grid-cols-4` to a
vertical stack, since it now lives in a ~288px-wide column, not the full
page width.

**Files involved:**
- `frontend/src/composables/useActionQueue.ts` (new) — shared alert
  registry (`ActionQueueAlert` type, `setAlerts`/`alerts`).
- `frontend/src/components/dashboard/ActionQueue.vue` (new) — collapsible
  right-hand feed; groups and renders the aggregated alerts.
- `frontend/src/components/dashboard/RosterWeaknessesWidget.vue`,
  `ContractDecisionsWidget.vue`, `PromotionReadyWidget.vue`,
  `PerformanceDeltasWidget.vue` (all modified) — each now calls
  `setAlerts` from its own fetch cycle.
- `frontend/src/views/LandingPage.vue` (modified) — two-column layout,
  `ActionQueue.vue` as a feed to the right of the main content.
