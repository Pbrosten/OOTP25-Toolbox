# Backend Review — Improvement Recommendations

Findings from a review of the SQL dump ingestion/processing pipeline
(`backend/app/db/staging.py`, `update.py`, `migration.py`, `projection.py`,
`service.py`, `jobs.py`, `cli.py`, and their SQL scripts). Companion to
[docs/wiki/Ingestion-Pipeline.md](../wiki/Ingestion-Pipeline.md), which
documents current behavior in detail — this document is the "what to do
about it" half.

**None of these are filed as tickets yet.** Each entry has enough detail
(problem, evidence, impact, suggested approach, files) to become one,
following [docs/tickets/TEMPLATE.md](../tickets/TEMPLATE.md), once
prioritized/accepted. Suggested tag and rough sizing are included per item.

## Priority summary

| # | Title | Severity | Tag | Effort |
|---|---|---|---|---|
| [1](#1-update-db-reprocesses-every-heap-on-every-run) | `update-db` reprocesses every heap on every run | High | feat | M |
| [8](#8-hardcoded-dev-config-and-secrets-printed-on-startup) | Hardcoded dev config and secrets printed on startup | High | fix | S |
| [2](#2-ratings-detail-inserts-arent-scoped-to-the-current-heap-date) | Ratings-detail inserts aren't scoped to the current heap date | Med-High | fix | S |
| [3](#3-cli-path-has-no-in-flight-job-protection) | CLI path has no in-flight-job protection | Medium | fix | M |
| [4](#4-retired-players-have-no-flag-and-silently-freeze) | Retired players have no flag and silently freeze | Medium | feat | M |
| [6](#6-projection-workers-depend-on-fork-semantics-for-flask-context) | Projection workers depend on `fork()` semantics for Flask context | Medium | refactor | M |
| [5](#5-staging-reset-logic-is-disabled) | Staging reset logic is disabled | Low-Med | chore | S |
| [9](#9-players_pitching-is-ingested-but-never-used) | `players_pitching` is ingested but never used | Low-Med | chore/feat | S (chore) / L (feat) |
| [10](#10-no-row-count-visibility-into-what-a-run-actually-changed) | No row-count visibility into what a run actually changed | Low | feat | S |
| [15](#15-rewrite-or-remove-16-stale-pipeline-tests) | Rewrite or remove 16 stale pipeline tests | Low (but noisy) | chore | M |
| [11](#11-remove-vestigial-sqlite-converter-registration) | Remove vestigial SQLite converter registration | Low | chore | XS |
| [7](#7-malformed-loggerdebug-call-in-update_player_age) | Malformed `logger.debug` call in `update_player_age` | Low | fix | XS |
| [12](#12-unused-statement_re-regex-naive-statement-splitting) | Unused `STATEMENT_RE` regex; naive statement splitting | Low | chore | S |
| [13](#13-fetch_projection_inputs-reads-cursor-after-its-with-block-closes) | `fetch_projection_inputs` reads cursor after its `with` block closes | Low | refactor | XS |
| [14](#14-repeated-run-script-rollback-commit-boilerplate) | Repeated run-script, rollback, commit boilerplate | Low | refactor | S |

Effort: **XS** = one-line/few-line fix, **S** = single file, few hours,
**M** = multiple files or needs a design decision, **L** = new subsystem.

---

## 1. `update-db` reprocesses every heap on every run

- **Severity:** High
- **Tag:** feat
- **Where:** `backend/app/db/staging.py::check_new_heaps()` (line 47)

**Problem.** `check_new_heaps()` lists every heap directory under
`DUMP_PATH` and returns all of them, every call — there's no persisted
record of which heaps have already been processed. A save with 3 years of
history (36 monthly + 3 yearly heaps) reprocesses all 39 heaps — full
staging reload, full migration SQL, full `multiprocessing.Pool(cpu_count())`
batter projection pass over every player — on *every* `update-db`
invocation, including ones where nothing on disk changed. Cost scales with
total heap count ever placed under `DUMP_PATH`, not with what's new.

This also makes `docs/wiki/Updating-the-Database.md`'s current claim
("`update-db` is safe to re-run — it only processes heaps it hasn't seen
before") inaccurate; that page should be corrected regardless of whether
this ticket is picked up.

**Impact.** As dump history grows, `update-db` run time grows unboundedly
even when the operator only wants to ingest this month's new heap. At some
save-history size this turns a few-second operation into a multi-minute
one, defeating the purpose of the async job work in ticket 0004.

**Recommended approach.** Track processed heaps persistently — e.g. a
`processed_heaps` table in `ootp` (heap path or `(year, month, is_short)` +
processed timestamp), written after a heap's migration commits
successfully. `check_new_heaps()` filters against it. Needs a decision on
what "already processed" means if the *dump file contents* change without
the directory name changing (unlikely given OOTP's export naming, but worth
stating as an explicit non-goal if so).

**Files involved:** `backend/app/db/staging.py`, `backend/app/db/service.py`
(pass processed-set through), a new migration/table, `backend/app/db/sql_scripts/schema.sql`.

---

## 2. Ratings-detail inserts aren't scoped to the current heap date

- **Severity:** Medium-High (performance; compounds with #1)
- **Tag:** fix
- **Where:** `backend/app/db/sql_scripts/migration/migration_short.sql`, the six `INSERT IGNORE ... FROM players_rating AS r JOIN staging.players_batting/players_fielding AS s ON r.player_id = s.player_id` statements (covering `players_batting`, `players_batting_talent`, `players_basepath`, `players_fielding`, `players_fielding_position`, `players_fielding_position_talent`)

**Problem.** None of these six statements filter by `r.rating_date =
'{{HEAP_DATE}}'`. Each one joins `players_rating` (which accumulates one row
per player *per heap ever processed*) against `staging.players_batting`/
`staging.players_fielding` (which only ever holds the *current* heap's
staged data, since staging is reloaded per heap). The result is correct —
`INSERT IGNORE` on the `rating_id` PK means old rows are never touched — but
the query re-evaluates the join against a player's entire rating history
every heap, instead of just the one new `rating_id` from this run.
`get_projection_inputs.sql` already does this correctly (`WHERE
r.rating_date = '{{HEAP_DATE}}'`) — same fix pattern applies here.

**Impact.** Six full-history joins per heap, scaling with total accumulated
`players_rating` rows. Directly compounds with #1 — every unnecessary
heap-reprocessing pays this cost six times over.

**Recommended approach.** Add `WHERE r.rating_date = '{{HEAP_DATE}}'` to
each of the six statements.

**Files involved:** `backend/app/db/sql_scripts/migration/migration_short.sql`.

---

## 3. CLI path has no in-flight-job protection

- **Severity:** Medium
- **Tag:** fix
- **Where:** `backend/app/db/cli.py::update_db_command` → `service.update_database()` directly

**Problem.** Ticket 0004 added a single-in-flight-job guard
(`app/db/jobs.py`'s `_lock`/`_jobs`), but only the `/api/admin/update-db`
route goes through it. `flask update-db` calls
`service.update_database()` directly. Two concurrent runs — two CLI
invocations, or one CLI run overlapping one API-triggered job — will both
load into the same `staging` schema concurrently (staging reset is disabled,
see #5) and each spin up their own `Pool(cpu_count())`, doubling CPU
contention and risking cross-run staging data contamination.

**Impact.** Low likelihood in a single-operator local tool, but the failure
mode (corrupted staging data feeding both runs' migrations) is silent and
hard to diagnose after the fact.

**Recommended approach.** Move the lock into `service.update_database()`
itself (or a shared module both `jobs.py` and `cli.py` call through), so
protection is guaranteed regardless of entry point, rather than living only
in the job-runner layer.

**Files involved:** `backend/app/db/service.py`, `backend/app/db/jobs.py`
(remove now-redundant locking, or keep as a thin wrapper), `backend/app/db/cli.py`.

---

## 4. Retired players have no flag and silently freeze

- **Severity:** Medium
- **Tag:** feat
- **Where:** `backend/app/db/sql_scripts/schema.sql` (`players` table), `migration_long.sql:31-46`, `migration_short.sql:1-10`

**Problem.** Both migration scripts filter `WHERE retired = 0` when reading
from `staging.players`, but `ootp.players` has no `retired` column at all.
Once a player retires in-game, their row simply stops receiving updates —
no new rating snapshots, no team/age refresh — with nothing in the schema
or API response indicating the data is frozen/stale.

**Impact.** The frontend (player search, player profile) will keep showing
a retired player's last-known team, age, and ratings indefinitely,
indistinguishable from an active player whose data just hasn't been updated
this month.

**Recommended approach.** Add a `retired BOOLEAN` column to `players`;
either (a) still filter retired players out of the ratings/age update path
but flip the flag to `true` via a small additional statement, or (b) do a
full upsert including retired status. Needs a decision on whether the API
should then start filtering retired players out of search results by
default, exposing a flag, or leaving that to the frontend — flag this as
open when filing the ticket.

**Files involved:** `backend/app/db/sql_scripts/schema.sql`,
`migration_long.sql`, possibly `backend/app/api/players.py` (if search
should exclude/flag retired players).

---

## 5. Staging reset logic is disabled

- **Severity:** Low-Medium
- **Tag:** chore
- **Where:** `backend/app/db/staging.py::connect_staging_db()`, lines 36-43 (commented out)

**Problem.** The `DROP TABLE`/`SET FOREIGN_KEY_CHECKS` staging-reset block
is fully commented out. Correctness currently depends entirely on each dump
file containing its own `DROP TABLE`/`CREATE TABLE` (standard `mysqldump`
per-table export behavior) — there are no sample dump fixtures in this repo
to confirm that holds for every table OOTP exports. If any included dump
file omits its own reset, staging tables silently accumulate cross-heap
data, contaminating the migration JOINs for that table.

**Impact.** Silent data corruption if the assumption ever breaks for one
table — hard to detect since `INSERT IGNORE` on the `ootp` side would mask
most symptoms.

**Recommended approach.** Either confirm (with a real OOTP dump export) that
every ingested file self-resets and delete the dead code with a comment
explaining the invariant it relies on, or re-enable the reset and measure
the cost (it's cheap — `SHOW TABLES` + one `DROP TABLE IF EXISTS` per table,
once per heap).

**Files involved:** `backend/app/db/staging.py`.

---

## 6. Projection workers depend on `fork()` semantics for Flask context

- **Severity:** Medium
- **Tag:** refactor
- **Where:** `backend/app/db/projection.py::process_player()` (line 27), called via `backend/app/db/update.py::project_players()`'s `multiprocessing.Pool(processes=cpu_count())` (line 160)

**Problem.** `process_player()` calls `current_app.logger.warning(...)`
inside a multiprocessing worker. This only works because Linux's default
`fork()` start method clones the parent's active app-context state into
each child — nothing in the code explicitly pushes a context in the worker.
If the start method ever changes (platform default differs, or a future
change calls `multiprocessing.set_start_method("spawn")`), every warning
call in a worker raises `RuntimeError: Working outside of application
context`, and since that call *is* the exception handler for the general
failure case, the error is unguarded and propagates out of
`pool.imap_unordered`, aborting the entire heap's projection pass.

**Impact.** Currently dormant (works fine on Linux/fork today), but fragile
— a Python version bump, a container base image change, or portability work
(e.g. running on macOS in dev, where `spawn` has been the default since
Python 3.8) could silently break every projection run.

**Recommended approach.** Make workers self-sufficient: pass a plain logger
(not `current_app.logger`) into worker processes, or initialize a minimal
app context explicitly in a `Pool` initializer function.

**Files involved:** `backend/app/db/projection.py`, `backend/app/db/update.py`.

---

## 7. Malformed `logger.debug` call in `update_player_age`

- **Severity:** Low (dormant)
- **Tag:** fix
- **Where:** `backend/app/db/update.py:72`

**Problem.** `logger.debug(current_date, birth_date)` passes a non-string
`date` object as the log message and `birth_date` as a positional
`%`-format arg. Currently dormant because the root logger is configured at
`INFO` (`app/__init__.py:21-24`), so `.debug()` short-circuits before
formatting. If debug logging is ever enabled for this logger,
`LogRecord.getMessage()` raises `TypeError`, aborting
`update_player_age()` mid-batch — and since that function commits every 500
rows (not once at the end), some ages would already be persisted before the
crash.

**Recommended approach.** Fix to
`logger.debug("current_date=%s birth_date=%s", current_date, birth_date)`
or remove — one-line fix.

**Files involved:** `backend/app/db/update.py`.

---

## 8. Hardcoded dev config and secrets printed on startup

- **Severity:** High
- **Tag:** fix
- **Where:** `backend/app/__init__.py:10` (`is_production = False`), `backend/app/__init__.py:17` (`print(app.config)`)

**Problem.** `is_production = False` is a literal, so `config.ProdConfig`
is unreachable dead code — every deployment runs with `DEBUG=True`,
`TESTING=True` regardless of environment, unless someone edits this source
line. Separately, `print(app.config)` unconditionally dumps the entire
Flask config — including `DB_PASSWORD` and `ADMIN_API_TOKEN` in plaintext —
to stdout/container logs on every process start.

**Impact.** Debug mode in a real deployment exposes the Werkzeug debugger
(arbitrary code execution via the interactive traceback) and verbose error
pages. The config print leaks the admin token and DB password into
container logs, which are typically retained/aggregated longer and more
broadly readable than the `.env` file itself.

**Recommended approach.** Derive `is_production` from an env var (e.g.
`FLASK_ENV`/a dedicated `APP_ENV`) instead of a hardcoded literal; remove
the `print(app.config)` line entirely (or replace with a redacted summary
logged at DEBUG level if startup visibility is wanted).

**Files involved:** `backend/app/__init__.py`, `backend/config.py`,
`backend/templates/.env-template` (document the new var).

---

## 9. `players_pitching` is ingested but never used

- **Severity:** Low-Medium
- **Tag:** chore (to stop the waste) or feat (to finish it)
- **Where:** `backend/app/db/staging.py::DUMP_INCLUSION_LIST` (line 12), every heap load

**Problem.** Every heap's pitching dump file is fully streamed and inserted
into `staging.players_pitching` (Stage 2 of the pipeline), but no migration
script, no `ootp` schema table, and no projection code (only
`BatterProjection` exists under `app/player_projection/`) ever reads it.
This lines up with `docs/wiki/Features.md`'s note that `PitcherPercentiles`
is a stubbed frontend placeholder — this is the backend half of the same
unfinished feature.

**Impact.** Pure wasted I/O/DB work on every heap load today. Not a
correctness issue.

**Recommended approach.** This is a product decision, not just a cleanup:
(a) if pitcher projections aren't planned soon, drop `players_pitching*`
from `DUMP_INCLUSION_LIST` and stop paying the ingestion cost (chore,
small); (b) if they are planned, this ingestion is already the first step —
scope a real "pitcher projection" epic analogous to
`docs/tickets/`'s admin-API epic (feat, large — schema table, migration SQL,
a `PitcherProjection` class, projection insertion, frontend
`PitcherPercentiles` implementation).

**Files involved:** `backend/app/db/staging.py` (if dropping), or a new
epic's worth of files (if pursuing).

---

## 10. No row-count visibility into what a run actually changed

- **Severity:** Low
- **Tag:** feat
- **Where:** `backend/app/db/service.py::update_database()`, `backend/app/db/update.py::process_single_heap()`

**Problem.** Nothing in the pipeline captures affected-row counts.
`service.update_database()`'s return payload
(`{"status": "ok", "heaps_processed": N, "long_heaps": X, "short_heaps": Y}`)
reports heaps *attempted*, not rows actually written. Combined with
`INSERT IGNORE` swallowing FK violations (documented in
`docs/wiki/Troubleshooting.md`'s "short heap against an empty players table
silently inserts nothing" gotcha), an operator can get a `status: "ok"` /
job `status: "succeeded"` result with zero net new data and no way to tell
from the API response alone.

**Recommended approach.** Have `process_single_heap()` return per-heap
counts (e.g. `cursor.rowcount` after each `INSERT`/`UPDATE`), aggregate them
in `service.update_database()`'s return dict — e.g.
`{"ratings_inserted": N, "players_updated": N, "projections_inserted": N}`.
Small, additive change to the existing return contract.

**Files involved:** `backend/app/db/update.py`, `backend/app/db/service.py`,
`backend/docs/openai.yaml` (update the `update-db`/`jobs` response schema).

---

## 11. Remove vestigial SQLite converter registration

- **Severity:** Low
- **Tag:** chore
- **Where:** `backend/app/db/connection.py::register_converters()` (lines 40-44), called unconditionally from `backend/app/db/__init__.py::init_app()`

**Problem.** `register_converters()` calls
`sqlite3.register_converter("timestamp", ...)` — a leftover from a
pre-MariaDB-migration version of the app. No `sqlite3` connection is opened
anywhere in the current pipeline. Harmless but dead code, and its
corresponding test (`test_connection.py::test_register_converters_registers_timestamp`)
is testing that dead code rather than anything load-bearing.

**Recommended approach.** Delete the function and its call site; delete or
repurpose the corresponding test.

**Files involved:** `backend/app/db/connection.py`,
`backend/app/db/__init__.py`, `backend/tests/db/test_connection.py`.

---

## 12. Unused `STATEMENT_RE` regex; naive statement splitting

- **Severity:** Low
- **Tag:** chore
- **Where:** `backend/app/db/staging.py:18` (`STATEMENT_RE`, defined, never used), `sql_dump_to_staging()` (line 78, actual splitting logic)

**Problem.** A quote-aware statement-splitting regex is defined but dead —
the real splitting logic in `sql_dump_to_staging()` is a simpler heuristic
(`line.strip().endswith(";")`), fine for standard one-statement-per-line
`mysqldump` output but would mis-split a line containing multiple
`;`-terminated statements. `connect_staging_db()` also doesn't set
`client_flag=CLIENT_MULTI_STATEMENTS`, so this isn't currently exercised
either way for OOTP's export format specifically.

**Recommended approach.** Either delete `STATEMENT_RE` (if the simple
line-based approach is intentionally sufficient for known dump formats —
document that assumption), or actually use it in `sql_dump_to_staging()` for
robustness against edge-case dump formatting.

**Files involved:** `backend/app/db/staging.py`.

---

## 13. `fetch_projection_inputs` reads cursor after its `with` block closes

- **Severity:** Low
- **Tag:** refactor
- **Where:** `backend/app/db/update.py:144-156`

**Problem.** `return [dict(row) for row in cursor.fetchall()]` is dedented
outside the `with db.cursor() as cursor:` block. This happens to work today
because pymysql's `Cursor.close()` doesn't clear the already-buffered
`self._rows` — but it relies on non-contractual internal cursor state rather
than fetching inside the `with` block as the code visually suggests.

**Recommended approach.** Move the `fetchall()`/dict-comprehension inside
the `with` block — purely a readability/robustness fix, no behavior change.

**Files involved:** `backend/app/db/update.py`.

---

## 14. Repeated run-script, rollback, commit boilerplate

- **Severity:** Low
- **Tag:** refactor
- **Where:** `backend/app/db/update.py::run_migration_short`, `run_migration_long`, `fetch_projection_inputs` (lines 97-156)

**Problem.** Three near-identical blocks: open a `.sql` resource, split on
`;`, execute each statement, `rollback()`+log+re-raise on exception or
`commit()` on success. Copy-pasted three times.

**Recommended approach.** Factor into one
`_run_sql_script(path, db, heap_date=None) -> Cursor` helper (accepting an
optional `inject_heap_date` call), used by all three call sites. Good
opportunity to fix #13 in the same pass.

**Files involved:** `backend/app/db/update.py`.

---

## 15. Rewrite or remove 16 stale pipeline tests

- **Severity:** Low severity (no real bug), but high noise cost
- **Tag:** chore
- **Where:** `backend/tests/db/test_connection.py` (2), `test_migration.py` (3), `test_projection.py` (2), `test_stagging.py` (3), `test_update.py` (6)

**Problem.** `tests/db/` currently runs at 16 failed / 24 passed. Every
failure targets a **removed** pre-MariaDB implementation (SQLite-backed
staging, `executescript()`, `inject_db_path()`/`STAGGING_DB_PATH`
templating, a tuple-of-two-lists `check_new_heaps()` return shape, direct
`db.executemany()`/`db.commit()` instead of cursor-scoped calls) — the
source was migrated to the current pymysql/two-database design but these
tests weren't updated alongside it. None of the 16 catch a real defect;
full reasoning per test is in
[docs/wiki/Ingestion-Pipeline.md §10](../wiki/Ingestion-Pipeline.md#10-test-coverage-status).

**Impact.** A perpetually red test suite for this module trains
contributors to ignore failures here, which is exactly the condition under
which a real regression would go unnoticed. It also means the pipeline's
actual current behavior — everything documented in
`docs/wiki/Ingestion-Pipeline.md` — has no regression coverage at all.

**Recommended approach.** Rewrite each against the current API (mirroring
the working patterns already in `test_service.py`/`test_jobs.py`, which
mock `get_db`/`close_db`/cursor context managers correctly), or delete and
replace with fresh coverage scoped to current behavior. Natural to pair with
whichever of #1–#14 gets picked up first, to lock in the *new* correct
behavior with a test rather than writing tests for code about to change
again.

**Files involved:** `backend/tests/db/test_connection.py`,
`test_migration.py`, `test_projection.py`, `test_stagging.py`,
`test_update.py`.
