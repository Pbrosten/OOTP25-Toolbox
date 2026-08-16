# 0071 — Align player-page surplus value with FV-based prospect value

- **Tag:** feat
- **Status:** Closed
- **Depends on:** [0056](0056-surplus-value-calculation.md), [0068](0068-prospect-fv-value-calculation.md)
- **Blocks:** —

## 1. Problem

Filed from a user report while reviewing the Prospect Pipeline (0069/0070)
against real player pages: the same prospect can show two disconnected
surplus-value stories depending on which page you're on.

`SurplusValue.vue`/`GET /api/players/<id>/surplus-value` (ticket 0056)
computes surplus value from a **signed contract** — projected value minus
what the player is actually owed, over his years of control. Most real
prospects have no `players_contract` row at all, so this route returns
`{"available": false}` for them (see 0056's missing-input handling), and the
player page shows "Surplus value not available for this player." The
Prospect Pipeline (0068/0069), by contrast, now computes a real FV-based
surplus value for the same player from his talent-ceiling projection,
independent of any contract. A GM looking at a prospect's own player page
today sees nothing, while the farm-system list right next to it shows a
real number.

## 2. Design choices

Resolved via a direct design conversation with the user:

- **Resolved — switching logic: unconditional, keyed on prospect status.**
  If the player currently qualifies as a prospect (0043's definition),
  the page always shows the FV-based value; otherwise it shows the
  contract-based value. Not a fallback-when-unavailable rule — a prospect
  who happens to have a real signed contract still sees the FV-based
  value, not the contract one. Chosen over showing both, to avoid mixing
  two methodologies on one page for a case (prospect-aged player with a
  real contract) that's rare in practice.
- **Resolved — where the logic lives: a new endpoint, chosen client-side.**
  `GET /api/prospects/<player_id>` (new route on the existing `prospects`
  blueprint, not `players.py`) reuses `get_prospects.sql` with its new
  optional `player_id` filter — a single-player-scoped reuse of the same
  query 0069 already built, not a parallel one. Returns
  `{"is_prospect": false}` when the player doesn't qualify, or
  `{"is_prospect": true, ...same "value" shape as GET /api/prospects'
  per-row "value" field, flattened...}` otherwise. `SurplusValue.vue`
  calls this first and only falls through to the existing
  `/api/players/<id>/surplus-value` fetch when `is_prospect` is false —
  the frontend never needs its own copy of 0043's prospect definition.
- **Resolved — presentation: a distinct mode, not a reshaped reuse.**
  `SurplusValue.vue` now branches on `mode` ('prospect' | 'contract').
  Prospect mode gets its own heading ("Prospect Value"), an explanatory
  note that this is a probabilistic farm-system valuation rather than a
  year-by-year contract projection, an FV grade badge (same tiering as
  `ProspectPipeline.vue`), an "MLB Promotion Ready" badge when applicable,
  and three stat tiles (expected surplus value, expected WAR, star odds)
  — no Extend/Keep/Non-tender recommendation badge, since 0058's labels
  describe contract decisions that don't apply here. Contract mode is
  untouched from 0057/0058.

## 3. Approach

- `backend/app/db/sql_scripts/api/get_prospects.sql`: added an optional
  `%(player_id)s` filter alongside the existing `team_id`/`position`/
  `level` ones.
- `backend/app/api/prospects.py`:
  - `get_prospects()` now passes `player_id: None` in its query params
    (SQL placeholder must always be bound).
  - New `GET /api/prospects/<int:player_id>` route (`get_prospect_value`):
    fetches one row via the same query, returns `{"is_prospect": False}`
    if none found, else `{"is_prospect": True, **_value_for(row)}` reusing
    the existing `_value_for` helper unchanged.
- `frontend/src/components/SurplusValue.vue`: fetches
  `/api/prospects/<id>` first; branches display mode on `is_prospect`;
  falls through to `/api/players/<id>/surplus-value` only when not a
  prospect. New prospect-mode template block per the presentation
  decision above.
- `backend/docs/openai.yaml`: documented the new endpoint.
- `backend/tests/api/test_prospects.py`: 3 new tests for
  `get_prospect_value` (not-a-prospect, is-a-prospect, player_id filter
  passthrough), plus updated the two existing filter-passthrough tests for
  the new `player_id: None` param.

**Post-implementation UI refinements (user feedback, same session):**
description trimmed to one sentence; FV moved into the same row as the
three stat tiles rather than its own row above them; that row uses
`flex` with the three stat tiles as `flex-1` (equal share of remaining
width) and FV as a fixed `flex-none w-16 h-16` square badge rather than
matching their width.

**Verified against real data** (`TEST.lg` save, backend container
restarted to pick up the change — `flask run` has no `--reload` flag, so a
bind-mount file change alone isn't enough):
- `GET /api/prospects/49722` (a real Phillies prospect, age 23): `{"is_prospect": true, "available": true, "fv": 50, ...}`.
- `GET /api/prospects/5` (a non-prospect): `{"is_prospect": false}`.
- Confirmed round-trip through the frontend dev server's Vite proxy
  (`localhost:5173/api/prospects/49722`) returns the identical shape.
- `SurplusValue.vue` compiles cleanly through Vite's SFC transform (no
  browser tool available this session to visually confirm rendering —
  same disclosed gap as 0070).

**Files involved:**
- `backend/app/db/sql_scripts/api/get_prospects.sql` (modified)
- `backend/app/api/prospects.py` (modified)
- `frontend/src/components/SurplusValue.vue` (modified)
- `backend/docs/openai.yaml` (modified)
- `backend/tests/api/test_prospects.py` (modified)
