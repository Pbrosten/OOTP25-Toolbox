# 0084 — Command Center: Action Queue

- **Tag:** feat
- **Status:** Open
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

A shared "alert" shape (e.g. `{ category, message, link }`) that each of
0079–0083's widgets can optionally emit alongside its normal display data
(not every widget necessarily has one — e.g. the team WAR aggregate is
just a stat, not an alert). This component collects whatever alerts are
present from the widgets rendered on the dashboard and renders them
grouped by `category`, each linking back to its source widget/page. No
new backend endpoint — purely a frontend aggregation of what the sibling
widget tickets already return.

**Files involved:**
- `frontend/src/components/dashboard/ActionQueue.vue` (new).
