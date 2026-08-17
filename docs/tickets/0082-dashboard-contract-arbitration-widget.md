# 0082 — Command Center: contract & arbitration decisions widget

- **Tag:** feat
- **Status:** Open
- **Depends on:** —
- **Blocks:** [0085](0085-gm-command-center-dashboard.md)

## 1. Problem

[0038](0038-gm-command-center.md) calls for surfacing upcoming
contract/arbitration decisions. The underlying logic already exists —
`GET /api/players/<id>/surplus-value` (from
[0056](0056-surplus-value-calculation.md)/[0058](0058-recommendation-thresholds.md))
returns a `recommendation` (Extend / Keep short-term / Let walk /
Non-tender / Trade before free agency) for arbitration-window players —
but it's per-player only. A roster-scoped dashboard widget calling it once
per player (25-40+ players) would be an N+1 fetch pattern.

## 2. Design choices

- **New bulk/team-scoped endpoint vs. per-player fetch loop from the
  frontend.** Chosen: a new bulk endpoint. Looping
  `/api/players/<id>/surplus-value` per roster player from the frontend is
  wasteful for a dashboard widget that just needs the subset of players
  with a non-null `recommendation` — a single backend query reusing the
  existing calc is both faster and simpler for the frontend to consume.

## 3. Approach

Add a new route (e.g. `GET /api/teams/<team_id>/contract-decisions`)
reusing 0056/0058's surplus-value/recommendation calculation across the
team's roster, returning only players with a non-null `recommendation`.
Frontend: a widget listing those players grouped by recommendation type,
scoped by `useCurrentTeam().currentTeamId`, linking each entry back to the
player's profile page (`SurplusValue.vue` already renders the full detail
there).

**Files involved:**
- `backend/app/api/teams.py` (modified) — new `contract-decisions` route,
  reusing the surplus-value calc module from 0056/0058.
- `frontend/src/components/dashboard/ContractDecisionsWidget.vue` (new).
