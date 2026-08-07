# Ticket Index

Tracks planned/in-progress/completed work for OOTP25-Toolbox. Each ticket is a
markdown file in this directory named `NNNN-short-slug.md`, containing: the
problem it solves, design choices (including outstanding/undecided ones), the
chosen approach and files involved, a tag, and a status.

**Tags:** `feat` | `fix` | `chore` | `refactor`
**Statuses:** `Open` | `In-Progress` | `Closed`

New tickets should start from [TEMPLATE.md](TEMPLATE.md) and be added to the
table below (and any relevant epic section) once created.

## Epic: Admin DB operations as API endpoints

Motivated by repeated local friction running `flask --app app init-db` /
`update-db` from the host `.venv` (host can't resolve the `mariadb` container
hostname or see `/data/dumps`, requiring manual env-var overrides every time).
Exposing the same operations as backend routes runs them inside the container
with correct config by construction, and additionally allows triggering them
from a `curl` request or a future UI button.

Suggested order: 0001 → 0002 → 0003 → 0004 → 0005. 0006 split off from 0005's
design discussion (log-tail progress needs backend work 0004 didn't do).

```
[x] 0001 DB service layer
      |
      v
[x] 0002 Admin API endpoints
      |
      +----------------------------+
      v                            |
[x] 0003 Auth guard                |
      |                            |
      v                            v
[x] 0004 Async update-db job <-----+
      |
      v
[x] 0005 Frontend trigger
      |
      v
[ ] 0006 Job log capture

[x] = Closed   [ ] = Open
```

| # | Title | Tag | Status | Depends on |
|---|-------|-----|--------|------------|
| [0001](0001-extract-db-service-layer.md) | Extract DB init/update logic into a reusable service layer | refactor | Closed | — |
| [0002](0002-admin-api-endpoints.md) | Admin API endpoints for init-db and update-db | feat | Closed | 0001 |
| [0003](0003-admin-api-auth-guard.md) | Guard admin endpoints with access control | feat | Closed | 0002 |
| [0004](0004-async-update-db-job.md) | Run update-db as an async background job with status polling | feat | Closed | 0002, 0003 |
| [0005](0005-frontend-admin-trigger.md) | Frontend trigger for admin DB operations | feat | Closed | 0004 |
| [0006](0006-job-log-capture.md) | Capture per-line logs for update-db jobs | feat | Open | 0004, 0005 |

## Backend pipeline improvements

Sourced from [docs/improvements/README.md](../improvements/README.md), a
review of the SQL dump ingestion/processing pipeline. Unlike the epic above,
these are largely independent — no fixed implementation order — except where
noted in a ticket's own Design choices section (e.g. 0014/0015 are
alternatives, not a sequence; 0021 folds into 0022).

| # | Title | Tag | Status | Depends on |
|---|-------|-----|--------|------------|
| [0007](0007-persist-processed-heaps.md) | Track processed heaps so update-db only ingests what's new | feat | Closed | — |
| [0008](0008-fix-prod-config-and-secret-logging.md) | Derive is_production from env; stop printing config with secrets | fix | Closed | — |
| [0009](0009-scope-ratings-detail-inserts-to-heap-date.md) | Scope ratings-detail inserts to the current heap date | fix | Closed | — |
| [0010](0010-cli-update-db-in-flight-lock.md) | Guard the CLI update-db path with the same in-flight-job lock as the API | fix | Closed | — |
| [0011](0011-retired-player-flag.md) | Add a `retired` flag so frozen player data is visible, not silent | feat | Closed | — |
| [0012](0012-projection-worker-app-context.md) | Stop relying on fork() semantics for Flask context in projection workers | refactor | Closed | — |
| [0013](0013-reenable-staging-reset.md) | Re-enable the staging DB reset before each load | chore | Closed | — |
| [0014](0014-drop-unused-pitching-ingestion.md) | Stop ingesting players_pitching until something reads it | chore | Closed | — |
| [0015](0015-pitcher-projection-epic.md) | Pitcher projections: schema, migration, and projection pipeline | feat | Open | — |
| [0016](0016-update-db-row-count-visibility.md) | Report row counts actually written by update-db | feat | Closed | — |
| [0017](0017-rewrite-stale-pipeline-tests.md) | Rewrite or remove 16 stale pipeline tests | chore | Closed | — |
| [0018](0018-remove-vestigial-sqlite-converter.md) | Remove vestigial SQLite converter registration | chore | Closed | — |
| [0019](0019-fix-malformed-logger-debug-call.md) | Fix malformed logger.debug call in update_player_age | fix | Closed | — |
| [0020](0020-unused-statement-re-regex.md) | Resolve unused STATEMENT_RE / naive statement splitting | chore | Closed | — |
| [0021](0021-fetch-projection-inputs-cursor-scope.md) | Fetch projection inputs inside the cursor's with block | refactor | Open | — |
| [0022](0022-consolidate-run-script-boilerplate.md) | Consolidate repeated run-script/rollback/commit boilerplate | refactor | Open | — |

## Frontend / stats display fixes

| # | Title | Tag | Status | Depends on |
|---|-------|-----|--------|------------|
| [0023](0023-fix-career-batting-rate-stats-display.md) | Fix OBP/SLG/OPS in the career batting stats table | fix | Open | — |
