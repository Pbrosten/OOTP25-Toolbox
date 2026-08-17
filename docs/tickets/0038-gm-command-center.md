# 0038 — GM Command Center

- **Tag:** feat
- **Status:** In-Progress
- **Depends on:** [0039](0039-roster-optimization-org-depth.md), [0042](0042-contract-arbitration-analyzer.md), [0043](0043-prospect-pipeline.md), [0065](0065-gm-org-selection-theming.md)
- **Blocks:** [0079](0079-dashboard-team-war-widget.md), [0080](0080-dashboard-over-underperformers-widget.md), [0081](0081-dashboard-roster-weaknesses-widget.md), [0082](0082-dashboard-contract-arbitration-widget.md), [0083](0083-dashboard-prospect-promotion-widget.md), [0084](0084-dashboard-action-queue.md), [0085](0085-gm-command-center-dashboard.md)

## 1. Problem

`docs/improvements/expanded-functionality.md`'s Tier 1 #1 ("GM Command
Center") calls for a single landing dashboard that tells the GM what needs
attention right now: standings/projected record, team WAR, over/underperformers,
injuries, upcoming contract/arbitration decisions, prospect promotion
opportunities, roster weaknesses/surpluses, and a prioritized "Action Queue"
of recommended actions.

Today `frontend/src/views/LandingPage.vue` is a bare launcher — it renders a
row of `ToolCard`s (currently just "Player Search") with no team or roster
content at all. There is no dashboard, no alerting, no notion of "the current
team" anywhere in the app (no session/team-selection concept exists in
`frontend/src/router/index.ts` or the backend API).

This is filed as an epic-tracker ticket, in the style of
[0015](0015-pitcher-projection-epic.md) — it's a large outline, not a scoped
implementation plan. It should be broken into per-widget/per-endpoint tickets
once prioritized, the way 0015 became 0024–0028.

## 2. Design choices

- **Data availability, re-checked 2026-08-16 now that 0039/0042/0043 are
  Closed.** Standings/schedule/win-loss and injury-state data still don't
  exist anywhere in `schema.sql` — those two widgets remain genuinely
  blocked, deferred out of v1 entirely (no sub-ticket filed for them).
  Everything else changed: 0042 shipped `players_contract`/
  `players_salary_history`/`players_service_time` and the
  recommendation-bearing `GET /api/players/<id>/surplus-value` endpoint;
  0043 shipped `GET /api/prospects` with an `mlb_promotion_ready` flag;
  0039 shipped `GET /api/teams/<id>/depth-chart` with per-position
  WAR-ranked rosters. Team WAR aggregation and over/underperformers
  (actual vs. projected WAR) also became buildable — `players_career_
  batting_stats.war`/`players_career_pitching_stats.war` (real-game WAR)
  now exist alongside the projected WAR tables, though no endpoint yet
  diffs or sums them.
- **"The current team."** Resolved by
  [0065](0065-gm-org-selection-theming.md) — `frontend/src/composables/
  useCurrentTeam.ts` (`currentTeamId`/`currentTeam`, `localStorage`-backed,
  set via the `/gm` org-selection page) is exactly the concept this
  ticket needed and didn't have to invent.
- **Build as a thin shell first, or after its dependencies?** Resolved:
  build last, after the widget tickets below ship — see
  [0085](0085-gm-command-center-dashboard.md)'s Design choices.
- **"Action Queue" ranking/prioritization logic.** Resolved with the user
  2026-08-16: a flat list grouped by category for v1, not real
  cross-widget priority/urgency scoring — see
  [0084](0084-dashboard-action-queue.md).
- **Dashboard placement.** Resolved with the user 2026-08-16: replaces
  `LandingPage.vue` (the Home page) rather than a new separate route —
  see [0085](0085-gm-command-center-dashboard.md).

## 3. Approach

Broken into sub-tickets 2026-08-16, the way 0015 became 0024–0028:

- [0079](0079-dashboard-team-war-widget.md) — team WAR aggregate widget
  (new backend endpoint).
- [0080](0080-dashboard-over-underperformers-widget.md) —
  over/underperformers widget (new backend endpoint, actual vs. projected
  WAR).
- [0081](0081-dashboard-roster-weaknesses-widget.md) — roster
  weaknesses/surpluses widget (classification logic still Outstanding).
- [0082](0082-dashboard-contract-arbitration-widget.md) — contract &
  arbitration decisions widget (new bulk endpoint reusing 0056/0058's
  calc).
- [0083](0083-dashboard-prospect-promotion-widget.md) — prospect
  promotion opportunities widget (frontend-only, reuses existing
  `/api/prospects` endpoint as-is).
- [0084](0084-dashboard-action-queue.md) — Action Queue, aggregating
  alerts from the five widgets above.
- [0085](0085-gm-command-center-dashboard.md) — the dashboard shell
  itself, replacing `LandingPage.vue`, composing all of the above.

Standings/projected-record and injuries remain out of scope — no ticket
filed for either, pending real data ingestion for both (would need their
own schema/migration work first, same shape as 0053/0054 did for
contract/salary).

**Files involved:** none directly — this ticket is the epic tracker; see
each sub-ticket's own Files involved.
