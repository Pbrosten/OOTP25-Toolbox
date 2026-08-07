# Ingestion Pipeline (Developer Reference)

[← Back to Home](Home.md)

This page documents how `update-db` / `init-db` actually work today, at the
code level — for the operator-facing "how do I run this" version, see
[Updating the Database](Updating-the-Database.md). Everything here reflects
the code as of this review; where current behavior is a known limitation
rather than a design choice, it's flagged and linked to
[`docs/improvements`](../improvements/README.md).

## 1. Topology

One MariaDB server, **two databases**:

- **`staging`** — raw, unmodified OOTP schema. Recreated table-by-table as a
  side effect of loading each dump file (see [§4](#4-stage-2--load-dump-files-into-staging)).
  Bootstrapped by `mariadb/init-staging.sql` (just `CREATE DATABASE staging`
  + grants — no tables; tables come from the dump files themselves).
- **`ootp`** — the app's main schema, defined in
  [`app/db/sql_scripts/schema.sql`](../../backend/app/db/sql_scripts/schema.sql)
  and created via `flask init-db` (destructive — drops and recreates all 14
  tables every time).

Both live in the same MariaDB instance, so migration SQL freely joins across
them (`FROM staging.players AS p ... JOIN ootp.players_rating ...`).

`app/db/connection.py::get_db()` opens the `ootp` connection with
`autocommit=False` (DictCursor) — callers must `commit()`/`rollback()`
explicitly. `app/db/staging.py::connect_staging_db()` opens the `staging`
connection with `autocommit=True` — every statement lands immediately.

## 2. Entry points

Three ways to trigger this pipeline, all converging on
`app/db/service.py::update_database()` / `init_database()`:

| Entry point | Path | Concurrency guard |
|---|---|---|
| CLI | `flask update-db` → `app/db/cli.py` → `service.update_database()` directly | MariaDB named lock (`GET_LOCK`/`RELEASE_LOCK`) inside `update_database()` itself |
| Sync API | `POST /api/admin/init-db` → `service.init_database()` directly | N/A (fast, DDL-only) — **not** guarded against an overlapping `update-db` run, see [docs/tickets/0010](../tickets/0010-cli-update-db-in-flight-lock.md)'s notes |
| Async job | `POST /api/admin/update-db` → `app/db/jobs.py::start_update_job()` → `service.update_database()` on a background thread | Both `jobs.py`'s own in-memory registry (fast synchronous `409` for an API-vs-API collision) *and* the same MariaDB lock as the CLI (catches a CLI-vs-API collision, surfaced as a failed job) |

`update_database()` acquires a server-side `GET_LOCK` before doing any work,
so every entry point shares the same guard regardless of which OS process
it's running in — a `threading.Lock` wouldn't do this, since the CLI runs as
its own separate process from the always-on API server. See
[docs/tickets/0010](../tickets/0010-cli-update-db-in-flight-lock.md).

## 3. Stage 1 — Discover heaps: `staging.py::check_new_heaps()`

```
DUMP_PATH/
  dump_2024_01/mysql/*.mysql.sql   (monthly = "short" heap)
  dump_2024_02/mysql/*.mysql.sql
  ...
  dump_2024_yearly/mysql/*.mysql.sql  (yearly = "long" heap)
```

`check_new_heaps()` lists `DUMP_PATH`, parses each directory name
(`dump_<year>_<month|"yearly">`), sorts the valid ones `(year, month)` with
yearly pinned to month `13` — so a save's yearly dump always sorts after
that year's monthlies, giving the correct seed-before-snapshot processing
order — then filters out any `(year, month)` already present in the
`processed_heaps` table (`get_processed_heap_keys()`), returning only what's
actually new.

`update.py::process_single_heap()` writes a `processed_heaps` row (via
`mark_heap_processed()`) only after that heap's migration/projection work
has fully committed, so a crash mid-heap leaves it eligible to be retried on
the next `update-db` run rather than being incorrectly marked done.

## 4. Stage 2 — Load dump files into staging

For each heap, `update.py::process_single_heap()`:

1. Opens a **fresh** `staging` connection (`connect_staging_db()` — not
   reused across heaps).
2. `load_sql_dumps_into_staging()` lists the heap's `mysql/` directory and
   loads any file matching `DUMP_INCLUSION_LIST` (`players.mysql`,
   `players_batting*`, `players_fielding*`,
   `players_career_batting_stats*`, `teams.mysql`) via
   `sql_dump_to_staging()`. (`players_pitching*` was dropped from this list
   — see [docs/tickets/0014](../tickets/0014-drop-unused-pitching-ingestion.md)
   — since nothing downstream ever read it: no migration script, no schema
   table in `ootp`, no projection code.)
3. `sql_dump_to_staging()` streams the file line by line (not loaded into
   memory whole), strips `#`-comment lines, buffers until a line ends in
   `;`, and executes each statement individually on a fresh cursor. Errors
   are logged (with a 200-char statement preview) and **re-raised** —
   nothing is silently swallowed here.
4. `connect_staging_db()` resets staging before loading: `SHOW TABLES` +
   `DROP TABLE IF EXISTS` for every table currently in `staging`, so a stale
   table from an earlier heap can't silently persist even if some dump file
   were to omit its own `DROP TABLE`/`CREATE TABLE`. See
   [docs/tickets/0013](../tickets/0013-reenable-staging-reset.md).

## 5. Stage 3a — Short (monthly) heap migration

`run_migration_short()` runs
[`migration_short.sql`](../../backend/app/db/sql_scripts/migration/migration_short.sql)
against the `ootp` connection, with `{{HEAP_DATE}}` substituted to
`YYYY-M-1` (`migration.py::inject_heap_date`). On any exception:
`db.rollback()` + re-raise; on success: `db.commit()`.

What the script does, in order:

1. `INSERT IGNORE INTO players_rating (player_id, rating_date, league_id) SELECT ... FROM staging.players WHERE retired = 0` — one row per non-retired player for this heap's date. `players_rating` has `UNIQUE(player_id, rating_date)`, which is what makes step 1 idempotent on re-run.
2. Six further `INSERT IGNORE ... FROM players_rating AS r JOIN staging.players_batting/players_fielding AS s ON r.player_id = s.player_id WHERE r.rating_date = '{{HEAP_DATE}}'` statements populate `players_batting`, `players_batting_talent`, `players_basepath`, `players_fielding`, `players_fielding_position`, `players_fielding_position_talent` — keyed off the `rating_id` just created in step 1, scoped to this heap's new rating row rather than a player's entire rating history. See [docs/tickets/0009](../tickets/0009-scope-ratings-detail-inserts-to-heap-date.md).
3. Three `UPDATE players SET position/bats/throws = CASE ... END` statements decode OOTP's numeric position/handedness codes into strings (`1`→`P`, `2`→`C`, ...; `1`→`R`, `2`→`L`, ...). These run unconditionally over the **entire** `players` table every heap, not just rows touched by this heap.

Then `fetch_projection_inputs()` runs
[`get_projection_inputs.sql`](../../backend/app/db/sql_scripts/migration/get_projection_inputs.sql)
— this one *does* correctly filter `WHERE r.rating_date = '{{HEAP_DATE}}'`
— joining `players` + `players_rating` + `players_batting` +
`players_basepath` + `players_fielding_position` into one row per player
rated this heap, returned as a list of dicts. This feeds Stage 4.

## 6. Stage 3b — Long (yearly) heap migration

`run_migration_long()` runs
[`migration_long.sql`](../../backend/app/db/sql_scripts/migration/migration_long.sql)
(no `{{HEAP_DATE}}` substitution — the script doesn't need the exact date).
Same rollback/commit pattern as short heaps.

1. Seeds a synthetic `team_id=999` "Free Agents" team (`INSERT IGNORE`).
2. `teams`: real upsert (`INSERT ... ON DUPLICATE KEY UPDATE`) from
   `staging.teams`.
3. `players`: upsert from `staging.players` (no longer filtered by
   `retired`, so a player who's retired since the last long heap still gets
   upserted), remapping OOTP's `team_id = 0` ("no team") sentinel to `999`.
   `team_id`, `prone_overall`, and `retired` are updated on conflict —
   everything else (name, birth_date, height/weight/bats/throws) is
   insert-only, never refreshed for an existing player. The `retired`
   column (added in [docs/tickets/0011](../tickets/0011-retired-player-flag.md))
   is the only signal that a player's ratings/team/age have stopped
   updating — the ratings/age-update paths still correctly skip retired
   players, this upsert just makes sure the flag itself gets set.
4. `players_career_batting_stats`: real upsert, filtered to
   `split_id = 1` (regular-season totals), PK `(player_id, year, team_id)`.

Then `update_player_age()`: loads **the entire `players` table** into memory
(`SELECT player_id, birth_date FROM players`), computes
`age = round((Jan 1 of heap year − birth_date).days / 365.25)` in Python,
and writes back in batches of 500 (`UPDATE ... WHERE player_id = %s`,
committing **per batch**, not once at the end — a mid-loop failure leaves
ages partially updated for that heap).

## 7. Stage 4 — Batter projections

Only short heaps produce projections. `project_players()` spins up
`multiprocessing.Pool(processes=cpu_count())` **once per heap** and maps
`process_player()` over every row `fetch_projection_inputs()` returned.

`process_player()` (`app/db/projection.py`) builds a
`BatterProjection(player)` (`app/player_projection/batter.py`) and calls
`calc_expected_stats()`, which runs a sabermetrics-style model:

- Looks up rate-stat contributions (HR%, K%, BB%, 3B-vs-2B split, etc.) from
  pickled lookup tables (`app/player_projection/constants/*.pkl`) keyed by
  each 20–80 OOTP rating.
- Applies a playing-time factor derived from the player's best defensive
  position (`def_pos_adj`) and an injury-proneness multiplier
  (`prone_overall` → Durable/Normal/Fragile/Wrecked bucket).
- Derives `AVG`/`OBP`/`SLG`/`wOBA`, then converts to runs: `wRAA` (vs. league
  wOBA `0.325`), baserunning runs, defensive runs (per 1350 assumed defensive
  innings), and a fixed replacement-level run rate, summed and divided by
  `9.92` runs/win for `WAR`.

Any exception during projection (including missing/`None` ratings) is caught
broadly, logged via a plain module-level `logging.getLogger(...)` (not
`current_app.logger` — workers run in separate `multiprocessing` processes
with no Flask app context, see
[docs/tickets/0012](../tickets/0012-projection-worker-app-context.md)), and
the player is silently dropped from the result set — no count of how many
players failed is ever surfaced.

`insert_projections()` batches results (1000 at a time) into
`players_batting_expected`, `players_basepath_expected`,
`players_fielding_expected`, and `players_run_value` via `INSERT IGNORE`
keyed on `rating_id` — re-running a heap that's already been projected is a
no-op for these tables (existing rows aren't overwritten, but also aren't
refreshed if the projection model itself changes).

## 8. Idempotency & re-run behavior — current status

| Scenario | What actually happens |
|---|---|
| Re-run `update-db` with no new dump files | `check_new_heaps()` returns nothing already recorded in `processed_heaps`, so no heap is reprocessed — a no-op run costs one query, not a full staging reload/migration/projection pass. |
| Re-run after a mid-heap crash | Per-heap migration SQL is transactional (`rollback()` on exception) for the migration steps, but `update_player_age()` commits per 500-row batch — a crash there leaves partial age updates for that heap. Since `mark_heap_processed()` only runs after the whole heap succeeds, a crashed heap is never recorded as processed and gets fully redone (ages overwritten again) on the next run. |
| Two `update-db` runs overlapping | Guarded regardless of entry point (CLI vs. CLI, CLI vs. API, API vs. API) by a MariaDB `GET_LOCK` inside `update_database()` itself. The second caller fails fast with `UpdateAlreadyRunningError` rather than loading into the same staging schema concurrently. `init-db` is **not** included in this guard — running it while an `update-db` job is in flight will still race. |
| A player retires in-game | `ootp.players.retired` gets flipped on the next long heap (full upsert, no longer filtered by `retired`), but their ratings/team/age still correctly stop updating — `retired` is the signal that data is now frozen, not a fix for the freeze itself. |

## 9. Data model quick reference

| Table | Populated by | Idempotency key |
|---|---|---|
| `teams` | long heap (upsert) | `team_id` PK, `ON DUPLICATE KEY UPDATE` |
| `players` | long heap (upsert, partial refresh) | `player_id` PK, `ON DUPLICATE KEY UPDATE` (`team_id`/`prone_overall`/`retired`) |
| `players_career_batting_stats` | long heap (upsert) | `(player_id, year, team_id)`, full `ON DUPLICATE KEY UPDATE` |
| `players_rating` | short heap | `UNIQUE(player_id, rating_date)`, `INSERT IGNORE` |
| `players_batting`, `players_batting_talent`, `players_basepath`, `players_fielding`, `players_fielding_position`, `players_fielding_position_talent` | short heap | `rating_id` (FK to `players_rating`), `INSERT IGNORE` |
| `players_batting_expected`, `players_basepath_expected`, `players_fielding_expected`, `players_run_value` | projection stage | `rating_id`, `INSERT IGNORE` |

## 10. Test coverage status

`tests/db/` passes in full, rewritten against the current pymysql/two-database
design documented above (see [docs/tickets/0017](../tickets/0017-rewrite-stale-pipeline-tests.md)).
`app/player_projection/` (batter projection math) and the `service.py`/
`jobs.py`/`cli.py` layers (covered by tickets 0001–0004) also have accurate,
passing test coverage. The only known-failing tests in the backend suite are
in `tests/api/test_players.py`, a pre-existing issue unrelated to this
pipeline.

## Known limitations at a glance

The limitations previously tracked here (unscoped ratings-detail inserts,
missing CLI concurrency guard, no retired-player flag, disabled staging
reset, `fork()`-dependent projection logging, unused `players_pitching`
ingestion, no row-count visibility, and dev-only config with secrets logged
on startup) have all been resolved — see
[docs/tickets](../tickets/index.md) 0008–0014 and 0016 for what changed and
why.

Still open: `init-db` isn't guarded against running concurrently with an
in-flight `update-db` job (see the idempotency table in [§8](#8-idempotency--re-run-behavior--current-status)).
Current and future work is tracked in [docs/tickets](../tickets/index.md).
