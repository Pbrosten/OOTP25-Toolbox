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
| CLI | `flask update-db` → `app/db/cli.py` → `service.update_database()` directly | **None** |
| Sync API | `POST /api/admin/init-db` → `service.init_database()` directly | N/A (fast, DDL-only) |
| Async job | `POST /api/admin/update-db` → `app/db/jobs.py::start_update_job()` → `service.update_database()` on a background thread | In-memory `_lock` + `_jobs` dict — only one job may be `pending`/`running` at a time |

The CLI path bypasses the job lock entirely — see
[docs/improvements](../improvements/README.md#3-cli-path-has-no-in-flight-job-protection).

## 3. Stage 1 — Discover heaps: `staging.py::check_new_heaps()`

```
DUMP_PATH/
  dump_2024_01/mysql/*.mysql.sql   (monthly = "short" heap)
  dump_2024_02/mysql/*.mysql.sql
  ...
  dump_2024_yearly/mysql/*.mysql.sql  (yearly = "long" heap)
```

`check_new_heaps()` lists `DUMP_PATH`, parses each directory name
(`dump_<year>_<month|"yearly">`), and returns every valid heap it finds,
sorted `(year, month)` with yearly pinned to month `13` — so a save's yearly
dump always sorts after that year's monthlies, giving the correct
seed-before-snapshot processing order.

> **Despite the name, this is not incremental.** It returns *every* heap
> currently on disk, every single call — there's no persisted record of
> what's already been processed. `update-db` reprocesses the entire dump
> history on every run. See
> [docs/improvements #1](../improvements/README.md#1-update-db-reprocesses-every-heap-on-every-run).

## 4. Stage 2 — Load dump files into staging

For each heap, `update.py::process_single_heap()`:

1. Opens a **fresh** `staging` connection (`connect_staging_db()` — not
   reused across heaps).
2. `load_sql_dumps_into_staging()` lists the heap's `mysql/` directory and
   loads any file matching `DUMP_INCLUSION_LIST` (`players.mysql`,
   `players_batting*`, `players_fielding*`, `players_pitching*`,
   `players_career_batting_stats*`, `teams.mysql`) via
   `sql_dump_to_staging()`.
3. `sql_dump_to_staging()` streams the file line by line (not loaded into
   memory whole), strips `#`-comment lines, buffers until a line ends in
   `;`, and executes each statement individually on a fresh cursor. Errors
   are logged (with a 200-char statement preview) and **re-raised** —
   nothing is silently swallowed here.
4. Table reset is implicit: staging table `DROP`/`CREATE` logic that used to
   run explicitly is now commented out (`staging.py:36-43`); staging tables
   are only reset because each dump *file* itself contains its own
   `DROP TABLE`/`CREATE TABLE` (standard `mysqldump` per-table export
   behavior).

`players_pitching*` files are loaded into `staging.players_pitching` but
**nothing downstream ever reads that table** — no migration script, no
schema table in `ootp`, no projection code. It's ingested and discarded
every heap. See [docs/improvements #9](../improvements/README.md#9-players_pitching-is-ingested-but-never-used).

## 5. Stage 3a — Short (monthly) heap migration

`run_migration_short()` runs
[`migration_short.sql`](../../backend/app/db/sql_scripts/migration/migration_short.sql)
against the `ootp` connection, with `{{HEAP_DATE}}` substituted to
`YYYY-M-1` (`migration.py::inject_heap_date`). On any exception:
`db.rollback()` + re-raise; on success: `db.commit()`.

What the script does, in order:

1. `INSERT IGNORE INTO players_rating (player_id, rating_date, league_id) SELECT ... FROM staging.players WHERE retired = 0` — one row per non-retired player for this heap's date. `players_rating` has `UNIQUE(player_id, rating_date)`, which is what makes step 1 idempotent on re-run.
2. Six further `INSERT IGNORE ... FROM players_rating AS r JOIN staging.players_batting/players_fielding AS s ON r.player_id = s.player_id` statements populate `players_batting`, `players_batting_talent`, `players_basepath`, `players_fielding`, `players_fielding_position`, `players_fielding_position_talent` — keyed off the `rating_id` just created in step 1.
   > **None of these six joins filter by `rating_date`.** Each one joins against a player's *entire* rating history, not just this heap's new row — `INSERT IGNORE` on the `rating_id` PK keeps the result correct, but the amount of work scales with total heaps ever processed, not just this one. See [docs/improvements #2](../improvements/README.md#2-ratings-detail-inserts-arent-scoped-to-the-current-heap-date).
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
3. `players`: upsert from `staging.players WHERE retired = 0`, remapping
   OOTP's `team_id = 0` ("no team") sentinel to `999`. Only `team_id` and
   `prone_overall` are updated on conflict — everything else (name,
   birth_date, height/weight/bats/throws) is insert-only, never refreshed
   for an existing player.
   > **Retired players are simply never updated again.** There's no
   > `retired` column on the `ootp.players` table at all — a retired
   > player's row just freezes at its last-known state with no signal
   > anywhere that it's stale. See
   > [docs/improvements #4](../improvements/README.md#4-retired-players-have-no-flag-and-silently-freeze).
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
broadly, logged via `current_app.logger.warning(...)`, and the player is
silently dropped from the result set — no count of how many players failed
is ever surfaced.

> `process_player` calls `current_app` from inside a multiprocessing worker.
> This only works because Linux's default `fork()` start method clones the
> parent's active Flask app context into each child; nothing in the code
> explicitly re-establishes it. See
> [docs/improvements #6](../improvements/README.md#6-projection-workers-depend-on-fork-semantics-for-flask-context).

`insert_projections()` batches results (1000 at a time) into
`players_batting_expected`, `players_basepath_expected`,
`players_fielding_expected`, and `players_run_value` via `INSERT IGNORE`
keyed on `rating_id` — re-running a heap that's already been projected is a
no-op for these tables (existing rows aren't overwritten, but also aren't
refreshed if the projection model itself changes).

## 8. Idempotency & re-run behavior — current status

| Scenario | What actually happens |
|---|---|
| Re-run `update-db` with no new dump files | Every heap ever placed under `DUMP_PATH` is reprocessed from scratch (staging reload + migration SQL + full projection pass). Net data is unchanged (`INSERT IGNORE`/upsert keys absorb the repeats), but the cost is paid every time. **Not free**, contrary to the impression given by "safe to re-run." |
| Re-run after a mid-heap crash | Per-heap migration SQL is transactional (`rollback()` on exception) for the migration steps, but `update_player_age()` commits per 500-row batch — a crash there leaves partial age updates for that heap. Re-running just redoes the whole heap; ages get overwritten again, so this self-heals on the next successful run. |
| Two `update-db` runs overlapping | Only guarded if **both** go through the Admin API job route. A CLI run has no lock and can overlap with anything. |
| A player retires in-game | Their `ootp.players` row stops receiving updates entirely (filtered out of every future heap's `staging.players` read via `WHERE retired = 0`) and is never marked retired in the main schema. |

## 9. Data model quick reference

| Table | Populated by | Idempotency key |
|---|---|---|
| `teams` | long heap (upsert) | `team_id` PK, `ON DUPLICATE KEY UPDATE` |
| `players` | long heap (upsert, partial refresh) | `player_id` PK, `ON DUPLICATE KEY UPDATE` (only `team_id`/`prone_overall`) |
| `players_career_batting_stats` | long heap (upsert) | `(player_id, year, team_id)`, full `ON DUPLICATE KEY UPDATE` |
| `players_rating` | short heap | `UNIQUE(player_id, rating_date)`, `INSERT IGNORE` |
| `players_batting`, `players_batting_talent`, `players_basepath`, `players_fielding`, `players_fielding_position`, `players_fielding_position_talent` | short heap | `rating_id` (FK to `players_rating`), `INSERT IGNORE` |
| `players_batting_expected`, `players_basepath_expected`, `players_fielding_expected`, `players_run_value` | projection stage | `rating_id`, `INSERT IGNORE` |

## 10. Test coverage status

`tests/db/` currently reports **16 failed, 24 passed**. All 16 failures are
against a **removed** pre-MariaDB implementation of this pipeline (SQLite
staging DB, `executescript()`/`inject_db_path()`/`STAGGING_DB_PATH`
templating, tuple-of-lists `check_new_heaps()` return shape) — the source
was migrated to the pymysql/two-database design documented above, but the
corresponding tests in `test_stagging.py`, `test_update.py`,
`test_migration.py`, `test_projection.py`, and `test_connection.py` were
not. **None of the 16 failures are catching a real defect** — they assert
against APIs that no longer exist. `app/player_projection/` (batter
projection math) and the newer `service.py`/`jobs.py`/`cli.py` layers
(covered by tickets 0001–0004) have accurate, passing test coverage.
Rewriting or removing the 16 stale tests is tracked in
[docs/improvements #15](../improvements/README.md#15-rewrite-or-remove-16-stale-pipeline-tests).

## Known limitations at a glance

- `update-db` is O(all heaps ever), not O(new heaps) — [#1](../improvements/README.md#1-update-db-reprocesses-every-heap-on-every-run)
- Ratings-detail inserts scan full rating history per player per heap — [#2](../improvements/README.md#2-ratings-detail-inserts-arent-scoped-to-the-current-heap-date)
- No concurrency guard on the CLI path — [#3](../improvements/README.md#3-cli-path-has-no-in-flight-job-protection)
- Retired players silently freeze, no flag — [#4](../improvements/README.md#4-retired-players-have-no-flag-and-silently-freeze)
- Staging table reset relies on dump files self-resetting — [#5](../improvements/README.md#5-staging-reset-logic-is-disabled)
- Projection workers depend on `fork()` semantics for Flask context — [#6](../improvements/README.md#6-projection-workers-depend-on-fork-semantics-for-flask-context)
- `players_pitching` ingested but never used — [#9](../improvements/README.md#9-players_pitching-is-ingested-but-never-used)
- No row-count/effect visibility in job results — [#10](../improvements/README.md#10-no-row-count-visibility-into-what-a-run-actually-changed)
- Config always runs as `DevConfig`; secrets printed on startup — [#8](../improvements/README.md#8-hardcoded-dev-config-and-secrets-printed-on-startup)

Full list with severities and suggested fixes: [docs/improvements/README.md](../improvements/README.md).
