# 0041 — Trade Target Finder

- **Tag:** feat
- **Status:** Open
- **Depends on:** —
- **Blocks:** —

## 1. Problem

`docs/improvements/expanded-functionality.md`'s Tier 1 #3 wants a filterable/
rankable search across the whole league — position, age, projected WAR,
years of control, salary, contract status, injury risk, prospect status,
role, team competitiveness, organizational fit — to surface realistic
acquisition targets (e.g. "25–30-year-old shortstops projected for 3+ WAR
with multiple years of control and affordable contracts") instead of the GM
manually searching the league.

`frontend/src/views/PlayerSearch.vue` + `app/api/players.py`'s `/search`
route exist today, but only for finding a specific known player, not
filtering/ranking the league by projection + contract criteria.

Filed as an epic-tracker ticket. Grouped with
[0042](0042-contract-arbitration-analyzer.md) (Contract & Arbitration
Analyzer) under the same Transactions-area epic — both need the same missing
contract/salary data (see Outstanding below), but neither strictly depends on
the other's implementation, so they're filed as siblings rather than a
dependency chain.

## 2. Design choices

- **Outstanding — no contract/salary data ingested.** Checked
  `backend/app/db/sql_scripts/schema.sql` and
  `backend/app/db/staging.py`'s `DUMP_INCLUSION_LIST`: there is no
  contract/salary/years-of-control table anywhere in `ootp` or `staging`
  today. `players.free_agent` (boolean) is the only contract-adjacent field
  that exists. Salary, contract status, and years-of-control — three of the
  source doc's listed filter criteria — can't be built without a new
  ingestion ticket (schema + migration for whatever contract table(s) the
  OOTP dump exposes — needs inspecting a real dump export to know the raw
  table/column names, same gap [0042](0042-contract-arbitration-analyzer.md)
  hits). Not resolved here; likely a shared prerequisite for both tickets in
  this epic.
- **Outstanding — injury risk.** No injury-history or current-injury-status
  table exists either. `players.prone_overall` is a durability *rating*
  input already consumed by `player_projection`'s constants
  (`INJ_CONSTANTS`, `backend/app/player_projection/batter.py:14-15`), which
  may be sufficient as an "injury risk" proxy — or the source doc may mean
  actual injury history, which isn't ingested. Not decided.
- **Outstanding — "team competitiveness" and "organizational fit" filters.**
  Both require knowing something about *other* teams' rosters/needs, not
  just the target player — competitiveness implies standings data (also
  missing, see [0038](0038-gm-command-center.md)'s Outstanding notes), and
  organizational fit implies cross-referencing against
  [0039](0039-roster-optimization-org-depth.md)'s depth-chart output for the
  GM's own team. Both are plausible v2 refinements rather than launch
  requirements; not decided whether v1 ships without them.
- **Resolved — what's buildable today without new ingestion.** Position, age,
  projected WAR (`players_run_value`/`players_pitching_run_value`), and role
  (existing `players.position`, pitcher `role` per
  [0026](0026-pitcher-projection-methodology.md)) are all already in `ootp`
  and sufficient for a reduced-scope v1 (filter/rank by these four, ignore
  contract/injury/competitiveness/fit until their data exists).

## 3. Approach (epic outline — needs further breakdown before implementation)

- Decide v1 scope: ship the reduced filter set (position/age/WAR/role) now,
  or wait on a contract-data ingestion ticket to cover the full source-doc
  feature set. This is the main thing to resolve when this ticket is
  actually started.
- Backend: a new search/filter+rank endpoint (extends `app/api/players.py`
  or a new `app/api/trade_finder.py`), parameterized filters over the
  existing WAR/age/position columns, ordered by projected WAR.
- Frontend: a new filterable results view, likely reusing
  `frontend/src/components/PlayerCard.vue`, under the source doc's suggested
  `TRANSACTIONS › Trade Target Finder` IA placement.

**Files involved:**
- TBD once broken into sub-tickets — likely `backend/app/api/players.py` or a
  new blueprint, plus a new frontend view. Contract-data ingestion (if
  pursued) would touch `schema.sql`, `staging.py`'s `DUMP_INCLUSION_LIST`,
  and the migration SQL, as its own separate ticket.
