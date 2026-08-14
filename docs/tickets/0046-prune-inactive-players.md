# 0046 — Prune players inactive before 2024; filter them at ingestion

- **Tag:** chore
- **Status:** Closed
- **Depends on:** —
- **Blocks:** —

## 1. Problem

`migration_long.sql`'s `INSERT INTO players` (lines 31-46) has no activity
filter at all — every row in `staging.players` gets upserted into
`ootp.players` unconditionally. `staging.players` mirrors the OOTP save's
full player pool: [0029](0029-pitcher-pitch-repertoire.md)'s dump inspection
found 134,808 rows in one sample save, "covering every player in the save's
history, not just active rosters." This app's stated product goal
(`docs/improvements/expanded-functionality.md`) is current-day GM
decision-support, not a full league-history archive.

Two concrete symptoms:
- Long-retired/historical players clutter search results — `players.py`'s
  `/search` (lines 59-88) matches on name only, no activity filter, so an
  old flavor-text player sharing a surname competes with current rosters.
- These players break the percentiles page: `players_rating` snapshots only
  exist from whenever ingestion started, so a player who stopped appearing
  in the league long before that has zero rating rows, and
  `BatterPercentiles`/`PitcherPercentiles` have no explicit handling for
  "this player has no ratings at all" — they either render empty or error,
  with nothing telling the user why.

## 2. Design choices

- **Resolved — what data defines "active."** Inspected a real dump export
  directly (`TEST.lg` save, `dump_2029_yearly`, current in-game date
  2030-01-01): `staging.players` has no last-active-year or debut/quit-year
  column (checked its full 116-column `CREATE TABLE`; the closest fields are
  `last_league_id`/`last_team_id`, which don't carry a year), so the
  ingestion-time filter has to read `MAX(year)` from
  `staging.players_career_batting_stats`/`_pitching_stats` directly, before
  the `players` INSERT decides whether to include a row. Confirmed this
  works well against the real data: of 134,808 players in the sample save,
  133,220 have at least one career-stat row (batting or pitching), of which
  16,129 last played in 2024 or later and 117,091 last played before
  2024 — i.e. the naive "last stat year < 2024" cut alone would remove ~87%
  of the table, matching the "deep sim history, mostly irrelevant" premise
  in the Problem section.
- **Resolved — the naive cutoff isn't sufficient on its own; `retired` has
  to gate it.** Checking `retired` against the same data surfaced a real
  edge case: 1,612 players have **zero** career-stat rows in either table
  (nothing to compare a year against at all), and 1,123 of those are **not**
  retired — sampled several: ages 16-28, mostly `team_id = 0`, i.e.
  not-yet-debuted prospects and international signees who are exactly the
  kind of player this app should keep (they're what the Prospect Pipeline
  epic, [0043](0043-prospect-pipeline.md), is about). A filter that prunes
  anyone without a recent stat row would delete all of them. Separately, 275
  **non-retired** players have career stats but their last one predates
  2024 (sampled: ages 24-28, unsigned free agents) — still in-game-active,
  just between teams. **Chosen: prune only players where `retired = 1` AND
  they have no career-stat row (batting or pitching) with `year >= 2024`.**
  `retired = 0` always wins regardless of stat recency — it's the
  authoritative "still in the league" signal; the year cutoff only applies
  to deciding whether an already-retired player is recent enough (e.g. a
  2025 retiree, kept) or historical filler (e.g. last played 1999, pruned).
- **Resolved — hard delete, not an archive flag.** The request was
  explicitly to prune players "from the database," not to hide them behind
  a flag — going with a real `DELETE`, mirroring
  [0011](0011-retired-player-flag.md)'s existing `retired` flag rather than
  adding a second status column for the same underlying concept.
- **Resolved — FK cascade: explicit dependency-ordered deletes, not a
  schema change.** Confirmed `schema.sql` declares no `ON DELETE CASCADE`
  anywhere. Chosen to keep it that way and have the one-time prune script
  delete leaf-to-root itself (batting/pitching/basepath/fielding
  expected → talent → base tables → run-value tables → `players_rating` →
  career-stats tables → `players`), rather than adding cascade behavior to
  the schema — a global `ON DELETE CASCADE` would silently widen the blast
  radius of *any* future `DELETE FROM players` app-wide, not just this
  one-time cleanup. Verified against an isolated throwaway MariaDB
  container (not the shared dev database) loaded with `schema.sql` and a
  synthetic fixture covering all five cases above (stale-retired w/
  rating-chain data, stale-retired w/ no stats, non-retired zero-stat
  prospect, non-retired stale-stat free agent, recently-retired,
  currently-active) — the script ran with no FK errors and left exactly the
  expected four non-pruned players and their rating-chain rows intact.
- **Resolved — 2024 cutoff.** Implemented literally as specified (a
  hardcoded `2024`, not a rolling "current heap year minus N" window). Since
  the save's in-game calendar keeps advancing past this hardcoded value
  (already at 2030 in the sample save), this cutoff will itself become
  stale over time and need revisiting later — a known limitation, not
  addressed here since the request was specifically "before 2024."
- **`players_similarity` — included in the prune script's cleanup, not
  treated as a cascade target.** It has no `ENGINE=InnoDB`/`FOREIGN KEY`
  declaration in `schema.sql` at all (looks vestigial, unrelated to this
  ticket otherwise), but still logically references `player_id` via
  `player_main`/`player_comp`, so the prune script deletes matching rows on
  either side of the pair for consistency.
- **Scope confirmed: two linked pieces of work.** A one-time prune script
  (written and verified against a throwaway DB only — **not yet run against
  the real `ootp` database**, per this project's standing rule on database
  changes) and an ongoing ingestion-time filter in `migration_long.sql`.
  Existing `ootp.players` rows that predate this filter and later become
  prune-eligible (e.g. a player who retires with no recent stats) aren't
  removed automatically by future heap runs — the filter only withholds new
  inserts of already-old players; actual removal of already-present stale
  rows is the one-time script's job.

## 3. Approach

- **Ingestion filter** — implemented in `migration_long.sql`'s `players`
  INSERT: added `WHERE s.retired = 0 OR s.player_id IN (SELECT player_id
  FROM recently_active_player_ids)`, where `recently_active_player_ids` is
  a small temp table precomputed just above it (see performance note below).
  Verified against a throwaway DB seeded with the same six fixture cases
  used for the prune-script test above — correctly kept the prospect, the
  stale-stat free agent, the recent retiree, and the active player, and
  excluded the two stale-retired cases.
- **Performance bug found and fixed while running this against the real dev
  database (not caught by the throwaway-DB tests above).** The filter was
  originally written as `WHERE s.retired = 0 OR EXISTS (SELECT 1 FROM
  staging.players_career_batting_stats cb WHERE cb.player_id = s.player_id
  AND cb.year >= 2024) OR EXISTS (... _pitching_stats ...)` — correct, but
  at real scale (staging's freshly-loaded, zero-index dump tables: ~670k
  batting rows, ~370k pitching rows, ~132k players) this made InnoDB take a
  shared lock on every row scanned while evaluating the correlated
  subqueries, under this app's connection settings (`autocommit=False`,
  REPEATABLE READ — `connection.py`). Observed via `SHOW ENGINE INNODB
  STATUS` against the real dev database: **over 1,000,000 row locks** held
  by a single `INSERT ... SELECT`, which didn't complete in 5+ minutes on
  one heap (previously looked identical to a hang — this is what actually
  broke the "reinitialize" attempt reported mid-ticket). Switching the
  session to `READ COMMITTED` cut the lock count to ~49 but didn't fix the
  wall-clock time, so the real fix was structural: precompute the small
  (~15k-row) recently-active player-ID set into an indexed
  `CREATE TEMPORARY TABLE` first, then filter the main INSERT against that
  instead of the two huge tables directly. Same real dump went from not
  completing in 5+ minutes to under 1.5 seconds total (temp table build +
  filtered INSERT). See the comment above the temp table in
  `migration_long.sql` for the short version.
- **One-time prune script** — new file
  `backend/app/db/sql_scripts/maintenance/prune_inactive_players.sql`. Not
  wired into any Flask CLI command — it's a standalone SQL script, meant to
  be run manually and deliberately, not part of the automated `update-db`
  path. Builds two temp tables (`prune_player_ids`, `prune_rating_ids`) then
  deletes leaf-to-root through every FK-dependent table before deleting
  `players` itself.
- **Verified end-to-end against the real dev database**, with explicit
  go-ahead: fresh `init-db`, then a full `update-db` run (66 heaps: 6
  long + 60 short) completed successfully with the fixed filter in place —
  `{"heaps_processed": 66, "players_updated": 926611, "ratings_inserted":
  8187194, "projections_inserted": 4226878}`. `ootp.players` landed at
  23,758 rows (vs. the ~130k+ a full unfiltered save would carry, per the
  Design choices estimate). Took a `mariadb-dump` backup immediately before
  running the prune script (also per project standing rule); the prune
  script then found nothing to remove, since the ingestion filter had
  already kept every stale row out from the start of this run — confirms
  the two pieces of work compose correctly (filter prevents new stale
  rows, prune script would catch pre-existing ones if any existed).
- **Separate, pre-existing issue surfaced but not fixed here:** while the
  slow (pre-fix) query above was running, a concurrent `init-db` call
  (unrelated to this ticket — no lock exists preventing `init-db` from
  running while `update-db` is in flight, unlike `update-db`-vs-itself
  which [0004](0004-async-update-db-job.md)/[0010](0010-cli-update-db-in-flight-lock.md)
  already guard) got queued mid-`DROP TABLE` and, once interrupted, left
  the schema half-rebuilt (several tables missing entirely). Recovered by
  re-running `init-db` cleanly once nothing else was running against the
  database. Worth its own ticket if this project wants `init-db` guarded
  the same way `update-db` already is — not scoped or fixed as part of
  0046.

**Files involved:**
- `backend/app/db/sql_scripts/migration/migration_long.sql` (modified)
- `backend/app/db/sql_scripts/maintenance/prune_inactive_players.sql` (new)
