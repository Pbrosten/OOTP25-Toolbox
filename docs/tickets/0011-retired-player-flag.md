# 0011 — Add a `retired` flag so frozen player data is visible, not silent

- **Tag:** feat
- **Status:** Closed
- **Depends on:** —
- **Blocks:** —

## 1. Problem

Both migration scripts filter `WHERE retired = 0` when reading from
`staging.players` (`migration_long.sql:31`, and implicitly `migration_short.sql`
via the `players_rating` join chain), but `ootp.players`
(`backend/app/db/sql_scripts/schema.sql:32-47`) has no `retired` column at
all. Once a player retires in-game, their row simply stops receiving
updates — no new rating snapshots, no team/age refresh — with nothing in the
schema or API response indicating the data is frozen/stale.

The frontend (player search, player profile) will keep showing a retired
player's last-known team, age, and ratings indefinitely, indistinguishable
from an active player whose data just hasn't been updated this month.

## 2. Design choices

- **Scope of this ticket.** Add the `retired` column and surface it in API
  responses; do **not** change search/filtering default behavior. Player
  search continues to return retired players exactly as it does today — the
  frontend decides whether/how to filter or badge them, as a separate
  follow-up if wanted. Keeps this ticket scoped to fixing the data-freshness
  visibility gap rather than bundling a search-behavior product decision.
- **How the flag gets set.** Options considered: (a) filter retired players
  out of the ratings/age update path as today, and additionally flip
  `retired` to `true` via a small extra statement once a player disappears
  from (or is marked retired in) `staging.players`; (b) do a full upsert of
  `ootp.players` including retired status every long heap, regardless of the
  `WHERE retired = 0` filter. **Chosen: (b)** — simpler to reason about (one
  upsert reflects current truth from the source data) and avoids a second
  pass to detect "player no longer appears among active players."
- **Outstanding:** whether the API should eventually expose retired-player
  filtering as a query param on player search is left for a follow-up
  ticket once frontend/product wants it — not blocking this one.

## 3. Approach

- `schema.sql`: add `retired BOOLEAN DEFAULT FALSE` to the `players` table.
- `migration_long.sql`: change the `INSERT INTO players ... ON DUPLICATE KEY
  UPDATE` block to also select/insert `retired` from `staging.players`
  (drop the `WHERE retired = 0` filter on this statement so retired players'
  `team_id`/`retired` status still gets upserted; the ratings/age-update
  paths keep their existing filters since a retired player shouldn't gain
  new snapshots).
- `backend/app/api/players.py`: include `retired` in player search/detail
  response payloads (no filtering change).
- `backend/docs/openai.yaml`: document the new `retired` field on player
  response schemas.

**Files involved:**
- `backend/app/db/sql_scripts/schema.sql` (modified)
- `backend/app/db/sql_scripts/migration/migration_long.sql` (modified)
- `backend/app/api/players.py` (modified)
- `backend/docs/openai.yaml` (modified)
