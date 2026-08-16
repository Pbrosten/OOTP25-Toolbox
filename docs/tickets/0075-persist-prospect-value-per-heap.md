# 0075 — Persist prospect FV/value per heap

- **Tag:** feat
- **Status:** Closed
- **Depends on:** —
- **Blocks:** [0076](0076-leaderboard-query-layer-api.md)

## 1. Problem

[0074](0074-league-wide-prospect-leaderboard.md) resolved that a
league-wide leaderboard needs 0068's FV/value calc persisted per heap,
not computed at request time — mirroring how `BatterProjection`/
`PitcherProjection`'s own output is already persisted into
`players_run_value`/`players_pitching_run_value` during `update-db`'s
heap processing, rather than recomputed live. Nothing currently persists
0068's talent+current calc anywhere; it only ever runs inside an HTTP
request (`app/api/prospects.py`).

## 2. Design choices

Resolved in 0074, restated at implementation-detail level:

- **New table, one row per `rating_id`** (same keying as
  `players_run_value`): `fv`, `surplus_value`, `expected_war`,
  `star_odds`, `current_fv`, `risk_tag`. `mlb_promotion_ready` is *not*
  stored — it depends on the player's team `level`, which the leaderboard
  query (0076) already has to join against `teams` fresh at read time
  anyway (same as 0069's live-compute path does today), so storing a
  level-dependent boolean here would go stale between heaps for no
  benefit; `current_fv >= 40` is recomputed cheaply at read time instead.
- **Computed for the same prospect-eligible candidate set 0069 already
  filters to** (age < 26, non-MLB affiliate or zero-service MLB rookie,
  excluding level 5/team_id 999 — 0043's definition), evaluated against
  `players`/`teams` state *at the heap being processed*, not "as of
  today." This doesn't need to be broader than the live definition: the
  leaderboard's read-time query (0076) re-validates eligibility against
  *current* `players`/`teams` state before ever reading this table (a
  player who ages past 26 or reaches the majors between heaps simply
  won't be joined back in), so a stale or narrow row here is harmless —
  it's a cache of the expensive part (the projection math), not of
  eligibility itself.
- **Short-heap-only, mirroring the existing projection pipeline.** Talent
  and current ratings only refresh on short (monthly) heaps — long/yearly
  heaps don't touch `players_rating`, so there's nothing new to compute
  for those, same reasoning `process_player`/`process_pitcher` already
  follow.
- **Row-building logic promoted out of `app/api/prospects.py` into
  `prospect_value.py`.** `_batter_projection_inputs`/
  `_pitcher_projection_inputs` (the talent/current input-dict slicing
  from a wide SQL row) currently live as private helpers in the API
  route. Both the new heap-processing step and the existing API route
  need the identical logic — promoted to public functions in
  `app/player_projection/prospect_value.py` (alongside
  `build_batter_talent_projection_input`/
  `build_pitcher_talent_projection_input`, which they already wrap), and
  `app/api/prospects.py` updated to import them instead of keeping its
  own copy. No behavior change to the existing endpoint.

## 3. Approach

- `backend/app/db/sql_scripts/schema.sql`: new `players_prospect_value`
  table (`rating_id` PK/FK into `players_rating`, `fv` INT,
  `surplus_value` INT, `expected_war` FLOAT, `star_odds` FLOAT,
  `current_fv` INT, `risk_tag` VARCHAR(1)).
- `backend/app/db/sql_scripts/migration/get_prospect_value_inputs.sql`
  (new): heap-dated (`{{HEAP_DATE}}` templating, matching
  `get_projection_inputs.sql`/`get_pitcher_projection_inputs.sql`)
  version of `get_prospects.sql`'s `prospect_candidates` CTE + wide
  current/talent column join — one row per prospect-eligible candidate at
  this heap, both batting-side and pitching-side columns always present
  (position gates which side gets used, same convention as
  `get_prospects.sql`).
- `backend/app/player_projection/prospect_value.py`: promote
  `_batter_projection_inputs`/`_pitcher_projection_inputs` here as public
  functions (naming TBD at implementation time to avoid colliding with
  the existing `build_*_talent_projection_input` names).
- `backend/app/db/projection.py`: new top-level `process_prospect(row)`
  (must be a module-level function, not a closure, for
  `multiprocessing.Pool` picklability — same constraint
  `process_player`/`process_pitcher` already satisfy), dispatching on
  `row["position"]` to `calculate_hitter_prospect_value`/
  `calculate_pitcher_prospect_value` via the promoted input builders;
  returns `None` on failure (mirrors `process_player`/`process_pitcher`'s
  existing try/except-and-log convention) rather than crashing the whole
  batch. New `prospect_value_proj_scripts` dict + batch dict shape
  (mirrors `proj_scripts`/`update_projection_batches`) for the
  `INSERT IGNORE` into `players_prospect_value`.
- `backend/app/db/update.py`: new `fetch_prospect_value_inputs`,
  `project_prospects` (mirrors `project_players`'s `Pool.imap_unordered`
  pattern), `insert_prospect_values` (mirrors `insert_projections`'s
  batching), wired into `process_single_heap`'s `short_heap` branch
  alongside the existing player/pitcher projection steps.
- Tests: `backend/tests/db/test_projection.py` (new `process_prospect`
  cases), `backend/tests/db/test_update.py` (new fetch/project/insert
  cases, mirroring existing player/pitcher projection test coverage),
  `backend/tests/player_projection/test_prospect_value.py` (tests for the
  promoted input-builder functions move/adapt as needed).

**Files involved:**
- `backend/app/db/sql_scripts/schema.sql` (modified)
- `backend/app/db/sql_scripts/migration/get_prospect_value_inputs.sql` (new)
- `backend/app/player_projection/prospect_value.py` (modified)
- `backend/app/api/prospects.py` (modified — import promoted helpers)
- `backend/app/db/projection.py` (modified)
- `backend/app/db/update.py` (modified)
- `backend/tests/db/test_projection.py` (modified)
- `backend/tests/db/test_update.py` (modified)
- `backend/tests/player_projection/test_prospect_value.py` (modified)

## 4. Implementation status

Code complete: `players_prospect_value` table added to `schema.sql`;
`get_prospect_value_inputs.sql` mirrors `get_prospects.sql`'s
prospect-definition filter, heap-dated; `batter_projection_inputs_from_row`/
`pitcher_projection_inputs_from_row`/`calculate_prospect_value_from_row`
promoted to `prospect_value.py` and `app/api/prospects.py` refactored to
use them (no behavior change — full suite still passing); `process_prospect`
+ `prospect_value_proj_scripts` + `update_prospect_value_batches` added to
`projection.py`; `fetch_prospect_value_inputs`/`project_prospects`/
`insert_prospect_values` added to `update.py` and wired into
`process_single_heap`'s short-heap branch. 197/197 backend tests passing
(new coverage: `process_prospect` success/none/exception,
`update_prospect_value_batches`, `project_prospects`,
`insert_prospect_values`, `fetch_prospect_value_inputs`, plus the promoted
row-slicing functions).

**Verification in progress (user running `update-db` against the real
save).** Surfaced one real finding along the way:

- **Fix: `calculate_prospect_value_from_row` returns `None` cleanly for a
  `position = 'P'` player with no matching `players_pitching` row at this
  heap**, instead of letting `PitcherProjection` raise
  `ValueError("Unrecognized pitcher role: None")` and get caught (and
  logged as `"Error processing prospect value for player X: ..."`) by the
  caller. Same class of sparse-data gap 0069 already found (Mason
  Brassfield/Boston Kellner) -- fully predictable from the row itself
  (`row["pitch_role"] is None`), not an exceptional condition, so it
  shouldn't need exception-based control flow or read as an error in the
  logs. Fixes the noise for *both* this heap-processing path and the
  existing live `GET /api/prospects` path, since both share
  `calculate_prospect_value_from_row`. New test:
  `test_calculate_prospect_value_from_row_missing_pitching_row_is_none`.
  198/198 backend tests passing after the fix.

- **Fix: `schema.sql` was missing a `DROP TABLE IF EXISTS
  players_prospect_value;` line.** `schema.sql` has always opened with a
  block of `DROP TABLE IF EXISTS` statements (one per table, in FK-safe
  order, no `SET FOREIGN_KEY_CHECKS`) so `init-db` can be re-run against
  an already-initialized database -- this ticket's own table addition
  missed adding its line to that block. Root cause of the user's `(1050,
  "Table 'players_prospect_value' already exists")` `init-db` failure:
  every table *before* mine in file order got dropped and recreated
  cleanly, but mine was never dropped, so its `CREATE TABLE` hit "already
  exists" and the exception aborted the whole statement loop (no
  try/except in `init_database()`) before ever reaching
  `players_similarity`/`players_contract`/`players_salary_history`/
  `players_service_time` -- exactly the missing-tables pattern observed
  live. Fixed: added the missing line; verified all 26 `CREATE TABLE`
  statements now have a matching `DROP TABLE IF EXISTS` (`diff` of the
  two name lists is empty).
- **Fix: `calculate_prospect_value_from_row` also short-circuits a
  position player with no `players_batting`/`players_batting_talent` row**
  (`bat_babip`/`bat_babip_talent` NULL). Found running `update-db`
  league-wide against the real save, right after the `init-db` fix above:
  `BatterProjection`'s rating lookups (`self.bat_constants.loc[rating,
  feature]`) raise `KeyError(None)` for a `None` rating, and
  `str(KeyError(None))` renders as the literally unhelpful message
  `"None"` -- exactly what showed up in the logs
  (`"Error processing prospect value for player X: None"`), for several
  players out of 5,843 league-wide candidates. Same sparse-data gap class
  as the pitcher-role fix above and 0069's original finding, not a real
  error. New tests:
  `test_calculate_prospect_value_from_row_missing_batting_row_is_none`
  (both the current-row-missing and talent-row-missing cases). 199/199
  backend tests passing.

**Final verification against real data**, after the fixes above landed and
a full schema + `update-db` recovery:
- `players_prospect_value` has real, per-heap persisted rows: 6,033-6,276
  rows per heap across the most recent heaps checked, scaling with each
  heap's own prospect-eligible candidate count.
- FV distribution across the latest heap is a real spread (80: 2, 70: 27,
  60: 153, 55: 234, 50: 403, 45: 628, 40: 1,168, 30: 3,418), not a flat
  default -- confirms the calc is genuinely differentiating players, not
  silently failing into one bucket.
- Spot-checked Cris Ortega (player 138746): his *latest* heap (2029-12-01)
  has complete, valid data for every column `get_prospect_value_inputs.sql`
  needs (confirmed by direct query -- no NULLs, unlike the genuine gaps
  the two fixes above were built to handle). Yet no `players_prospect_value`
  row exists for his `rating_id` at that heap, even though 6,033 other
  players from the same heap do. Root cause: that
  heap was processed by an earlier version of the code (before one of the
  two bugfixes above landed), and `update-db` only processes heaps not
  already in `processed_heaps` -- it won't automatically retry a heap
  that's already marked done just because the code changed. **Not a
  current defect** (confirmed today's code would compute a real value for
  him if this heap ran now) -- a known, accepted artifact of iterative
  testing across bugfixes within a single save's cumulative heap history,
  per the user's explicit call not to force a full clean re-run just to
  clear it. A future full `init-db` + `update-db` pass would naturally
  produce a gap-free dataset.
