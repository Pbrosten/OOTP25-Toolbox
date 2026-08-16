# 0071 — Align player-page surplus value with FV-based prospect value

- **Tag:** feat
- **Status:** Open
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

None resolved yet — filed as a scoping ticket per the user's explicit
request, not implemented here.

- **Outstanding — switching logic.** When should the player page prefer
  the FV-based value over the contract-based one? Options: (a) "player
  currently qualifies as a prospect per 0043's definition → always show
  FV value instead of contract value," (b) "no contract-based value
  available → fall back to FV value if the player is prospect-eligible,"
  (c) show both side by side with distinct labels whenever both apply.
  Needs a real decision — (a)/(b) risk hiding a legitimate contract-based
  number for an arb-eligible prospect-aged player with a real deal on
  file; (c) risks confusing two different methodologies on one page.
- **Outstanding — where the decision lives.** Should
  `GET /api/players/<id>/surplus-value` itself absorb this logic (extend
  the route to try FV-based value when contract-based comes back
  unavailable), or should the frontend call both
  `/api/players/<id>/surplus-value` and a per-player slice of 0069's
  logic and choose client-side? The latter likely needs a new single-
  player endpoint mirroring 0069's per-row calc, since
  `GET /api/prospects` is org-scoped, not player-scoped.
- **Outstanding — presentation.** The two calculations don't share a
  shape: contract-based value is a year-by-year table with an
  Extend/Keep/Let-walk/Non-tender/Trade recommendation (0058); FV-based
  value is a single expected-value figure plus star odds and an FV grade.
  `SurplusValue.vue` needs a real design pass to present whichever one
  applies without implying the other methodology's guarantees (e.g. FV
  value is a probabilistic expectation across many historical
  comparables, not a year-by-year projection like the contract model).

## 3. Approach

TBD — blocked on the Outstanding questions above being resolved with the
user before implementation starts, same convention as other tickets in
this project with unresolved design questions.

**Files involved:**
- TBD.
