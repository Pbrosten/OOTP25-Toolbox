# 0009 — Scope ratings-detail inserts to the current heap date

- **Tag:** fix
- **Status:** Closed
- **Depends on:** —
- **Blocks:** —

## 1. Problem

In `backend/app/db/sql_scripts/migration/migration_short.sql`, six
`INSERT IGNORE ... FROM players_rating AS r JOIN staging.players_batting/
staging.players_fielding AS s ON r.player_id = s.player_id` statements
(covering `players_batting`, `players_batting_talent`, `players_basepath`,
`players_fielding`, `players_fielding_position`,
`players_fielding_position_talent`) don't filter by
`r.rating_date = '{{HEAP_DATE}}'`.

Each one joins `players_rating` (which accumulates one row per player *per
heap ever processed*) against `staging.players_batting`/
`staging.players_fielding` (which only ever holds the *current* heap's
staged data, since staging is reloaded per heap). The result is correct —
`INSERT IGNORE` on the `rating_id` PK means old rows are never touched — but
the query re-evaluates the join against a player's entire rating history
every heap, instead of just the one new `rating_id` from this run.
`get_projection_inputs.sql` already does this correctly (`WHERE
r.rating_date = '{{HEAP_DATE}}'`) — this ticket applies the same fix
pattern to `migration_short.sql`.

Six full-history joins per heap, scaling with total accumulated
`players_rating` rows. Directly compounds with
[0007](0007-persist-processed-heaps.md) — every unnecessary
heap-reprocessing pays this cost six times over.

## 2. Design choices

Chosen approach, no real alternatives considered: add
`WHERE r.rating_date = '{{HEAP_DATE}}'` to each of the six statements,
matching the existing pattern in `get_projection_inputs.sql`. This is a pure
performance fix with no behavior change (verified by the `INSERT IGNORE`
argument above), so no design trade-off to weigh.

## 3. Approach

- Add `WHERE r.rating_date = '{{HEAP_DATE}}'` to the six `INSERT IGNORE`
  statements in `migration_short.sql` that currently join
  `players_rating`/`staging.players_batting` or
  `players_rating`/`staging.players_fielding` without a date filter.
- No schema or application code changes needed — `{{HEAP_DATE}}` is already
  injected into this script via `inject_heap_date()`
  (`backend/app/db/migration.py`) before execution.

**Files involved:**
- `backend/app/db/sql_scripts/migration/migration_short.sql` (modified)
