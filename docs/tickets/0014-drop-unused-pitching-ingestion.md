# 0014 — Stop ingesting players_pitching until something reads it

- **Tag:** chore
- **Status:** Closed
- **Depends on:** —
- **Blocks:** —

## 1. Problem

Every heap's pitching dump file is fully streamed and inserted into
`staging.players_pitching` (`DUMP_INCLUSION_LIST` in
`backend/app/db/staging.py:8-15`), but no migration script, no `ootp` schema
table, and no projection code (only `BatterProjection` exists under
`backend/app/player_projection/`) ever reads it. This lines up with
`docs/wiki/Features.md`'s note that `PitcherPercentiles` is a stubbed
frontend placeholder — this is the backend half of the same unfinished
feature.

Pure wasted I/O/DB work on every heap load today. Not a correctness issue.

## 2. Design choices

This is the "stop the waste now" half of a two-way fork with
[0015](0015-pitcher-projection-epic.md) (the "finish the feature" epic). They
are alternatives at the product level (pitcher projections either aren't a
near-term priority, in which case this ticket applies, or they are, in which
case 0015 supersedes this one and re-adds the ingestion as its first step).
Filing both lets whichever gets picked up first proceed without waiting on a
product decision neither ticket owns; if 0015 is picked up before this one
ships, close this ticket as superseded.

Chosen approach for this ticket specifically: remove the ingestion, no
alternative considered — the only other option (leave it as dead weight
"just in case") is the status quo this ticket exists to fix.

## 3. Approach

- Remove `"players_pitching"` from `DUMP_INCLUSION_LIST` in
  `backend/app/db/staging.py:8-15`.
- Confirm no other code path references `staging.players_pitching` (grep
  found none as of this writing — `migration_short.sql`/`migration_long.sql`
  only join `players_batting`/`players_fielding`).
- No schema change needed — `staging.players_pitching` is created by the
  dump file's own `CREATE TABLE` statement when loaded, so simply not
  loading it means the table never gets created in `staging`, which is fine
  since nothing depends on its existence there.

**Files involved:**
- `backend/app/db/staging.py` (modified — remove list entry)
