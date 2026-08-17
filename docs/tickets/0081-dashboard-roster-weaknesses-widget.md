# 0081 — Command Center: roster weaknesses/surpluses widget

- **Tag:** feat
- **Status:** Open
- **Depends on:** —
- **Blocks:** [0085](0085-gm-command-center-dashboard.md)

## 1. Problem

[0038](0038-gm-command-center.md) calls for flagging roster
weaknesses/surpluses by position. The raw data exists —
[0063](0063-roster-depth-chart-query-api.md)'s
`GET /api/teams/<id>/depth-chart` already returns every position's
players ranked by WAR, per level — but there's no classification of which
positions actually count as "thin" or "deep." That scoring layer doesn't
exist yet.

## 2. Design choices

- **Outstanding: weakness/surplus thresholds.** What makes a position a
  "weakness" (e.g. no projected-average-or-better MLB option) vs. a
  "surplus" (multiple above-average options blocking each other at the
  same level) isn't decided here. `BatterPercentiles.vue`/
  `PitcherPercentiles.vue` already compute percentile bands for
  individual players' value stats — reusing that percentile framing
  (e.g. "no player above the Nth percentile at this position") is the
  likely direction, but the exact cutoffs need a design pass against real
  roster data before implementation, not decided here.
- **Backend vs. client-side computation.** Since the depth-chart endpoint
  already returns the needed per-position WAR-ranked data, this
  classification could run client-side against the existing response
  rather than requiring a new endpoint. Leaning client-side to avoid
  another round-trip, but not finalized — depends on how much filtering
  logic the threshold decision above ends up needing.

## 3. Approach

Not fully scoped pending the Outstanding threshold question above. Likely:
a classification function (frontend or a new lightweight backend
endpoint) applied to the existing depth-chart response, producing a
weakness/surplus list per position/level. Frontend: a widget rendering
that list, scoped by `useCurrentTeam().currentTeamId`.

**Files involved:**
- `frontend/src/components/dashboard/RosterWeaknessesWidget.vue` (new).
- Possibly `backend/app/api/teams.py` (modified), TBD per the Outstanding
  question above.
