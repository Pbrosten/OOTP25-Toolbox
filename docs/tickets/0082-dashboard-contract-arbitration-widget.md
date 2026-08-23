# 0082 — Command Center: contract & arbitration decisions widget

- **Tag:** feat
- **Status:** Closed
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

Reusing 0056/0058's calculation meant extracting it first: the per-player
route's logic (base_war from batting/pitching WAR, contract/service-time
availability checks, `calculate_surplus_value` +
`recommend_contract_action`) was inlined directly in
`get_player_surplus_value`, so a second caller would have had to
copy-paste it. Factored out as
`compute_surplus_value_and_recommendation(row)` in
`app/player_projection/contract_value.py` — a pure refactor of the
existing route (verified against its existing test suite, unchanged
behavior), now shared by both routes.

Added `GET /api/teams/<team_id>/contract-decisions` to
`backend/app/api/teams.py`, backed by a new `get_team_contract_inputs.sql`
(the same per-player shape as 0056's `get_player_contract_inputs.sql`,
just for the whole roster in one query — pitchers included, unlike
0081's position-players-only roster-strength widget, since contract
decisions apply to the whole roster). For each roster row, calls
`compute_surplus_value_and_recommendation` and keeps only players who
came back with an actual `recommendation` (arbitration-window players
with a computable surplus value) — everyone else, including a fully
computable surplus value outside the arb window, is silently excluded,
since the widget only cares about live decisions. Frontend:
`ContractDecisionsWidget.vue` groups the returned players by
recommendation (`Extend`/`Keep short-term`/`Trade before free
agency`/`Let walk`/`Non-tender`, same color coding as
`SurplusValue.vue`'s `recommendationClass`), scoped by
`useCurrentTeam().currentTeamId`, linking each entry to the player's
profile page (`SurplusValue.vue` already renders the full year-by-year
detail there).

Post-close correction, per the user 2026-08-23: rolling this widget out
onto real roster data surfaced a real bug in 0058's original
`recommend_contract_action`, not a widget-specific issue — a real
already-fully-extended player (every remaining projected year already
`source: "contract"`, none reverting to an arbitration/pre-arb estimate)
was returning `"Extend"` purely because their average surplus exceeded
the threshold, with no check for whether there was anything left to
extend. Fixed at the source: `recommend_contract_action` now returns
`None` (no live decision) whenever every remaining year is already
locked in under a signed contract — the same `discretionary` check the
function already used to gate `Non-tender`, now applied uniformly before
`Extend`/`Keep short-term`/`Non-tender` are considered at all, not just
`Non-tender`. This also fixes the analogous "Let walk" mislabel for an
already-signed *negative*-surplus contract (an albatross deal the team
is stuck with, not a free-walk decision) — same root cause, same fix.
Regression-tested directly against the reported real case (a fully-
extended, high-surplus player) in
`tests/player_projection/test_contract_value.py`.

**Files involved:**
- `backend/app/player_projection/contract_value.py` (modified) —
  extracted `compute_surplus_value_and_recommendation`; fixed
  `recommend_contract_action` to return `None` for an already
  fully-extended player.
- `backend/app/api/players.py` (modified) — `get_player_surplus_value`
  now calls the shared helper instead of inlining the logic.
- `backend/app/api/teams.py` (modified) — new `contract-decisions` route.
- `backend/app/db/sql_scripts/api/get_team_contract_inputs.sql` (new) —
  team-scoped contract-input rows, one query for the whole roster.
- `frontend/src/api/teams.ts` (modified) — `fetchTeamContractDecisions` +
  `ContractDecisions`/`ContractDecisionPlayer`/`ContractRecommendation`
  types.
- `frontend/src/components/dashboard/ContractDecisionsWidget.vue` (new).
- `frontend/src/views/LandingPage.vue` (modified) — widget wired into
  the dashboard shell's "Roster Insights" section.
