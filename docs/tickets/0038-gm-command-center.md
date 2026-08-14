# 0038 — GM Command Center

- **Tag:** feat
- **Status:** Open
- **Depends on:** —
- **Blocks:** —

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

- **Outstanding — most of this dashboard's inputs don't exist in `ootp` yet.**
  Checked `backend/app/db/sql_scripts/schema.sql` directly: there is no
  standings/schedule/win-loss table, no contract/salary/arbitration table, and
  no injury table. `players` has only `age`, `position`, `team_id`,
  `free_agent`, `prone_overall` (durability proxy, no active-injury state).
  Several Command Center widgets (standings/playoff outlook, contract &
  arbitration decisions, injuries) are blocked on data this app doesn't
  ingest today — see [0041](0041-trade-target-finder.md)/[0042](0042-contract-arbitration-analyzer.md)'s
  own Outstanding notes, which hit the same gap for contract/salary data.
  Widgets buildable from what's already ingested: team/projected WAR (from
  `players_run_value`/`players_pitching_run_value` aggregated by `team_id`),
  roster weaknesses/surpluses (feeds from [0039](0039-roster-optimization-org-depth.md)),
  prospect promotion opportunities (feeds from [0043](0043-prospect-pipeline.md)).
- **Outstanding — "the current team."** Nothing in the app models "which team
  is the GM's team" today (no user/session/team-selection concept). The
  dashboard needs a `team_id` to scope everything to. Needs its own design
  pass: a settings/config value, a login-adjacent concept, or a route param —
  not decided here.
- **Outstanding — build as a thin shell first, or after its dependencies?**
  Every "Primary output" bullet in the source doc is itself sourced from a
  different epic ([0039](0039-roster-optimization-org-depth.md) for
  roster weaknesses, [0043](0043-prospect-pipeline.md) for promotion
  readiness, [0042](0042-contract-arbitration-analyzer.md) for contract
  decisions). Building Command Center first means a shell with placeholder/
  empty sections that fill in as sibling epics ship; building it last means
  no landing page value until everything else is done. **Not decided** —
  worth resolving before scoping the Approach below into real tickets, since
  it changes whether this ticket blocks on the others or they block on it.
- **Outstanding — "Action Queue" ranking/prioritization logic.** The source
  doc's example alerts ("Bullpen projected to be a major weakness", "Prospect
  blocked by organizational depth") imply a cross-cutting priority/urgency
  score, not just a concatenation of each sibling epic's own alerts. What
  that ranking function looks like (and whether it's even needed for a v1 —
  a flat list grouped by category might suffice) is unresolved.

## 3. Approach (epic outline — needs further breakdown before implementation)

- Resolve the "current team" and shell-vs-last-built Outstanding questions
  above first; they determine whether this can start independently or should
  wait on 0039/0042/0043.
- Backend: a new `app/api/dashboard.py` (or similar) blueprint that composes
  data already exposed by (or added to) the players/ratings/projections
  blueprints, scoped by `team_id`. Each widget likely becomes its own query
  rather than one giant aggregate endpoint, so the frontend can render
  incrementally/independently per section.
- Frontend: replace or extend `LandingPage.vue` with a real dashboard layout
  (or a new `/team/:id` route + component, leaving `LandingPage.vue` as the
  tool launcher it already is) — matches the source doc's top-level
  `GM COMMAND CENTER` position in the suggested information architecture.
- Action Queue: a dedicated component that renders alerts from whichever
  sibling widgets are available, each with a "why" (per the source doc's
  Cross-Cutting Design Principle #4) linking back to the page that explains
  it.

**Files involved:**
- TBD once broken into sub-tickets — likely `backend/app/api/dashboard.py` (new),
  `frontend/src/views/LandingPage.vue` (modified) or a new dashboard view,
  `frontend/src/router/index.ts` (modified).
