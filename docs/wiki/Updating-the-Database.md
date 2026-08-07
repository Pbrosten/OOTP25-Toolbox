# Updating the Database

[← Back to Home](Home.md)

OOTP exports per-table `.mysql.sql` dump files into
`saved_games/<save>/dump/`:

- `dump_YYYY_MM/mysql/` — **monthly** ("short") heap: rating/stat snapshots.
- `dump_YYYY_yearly/mysql/` — **yearly** ("long") heap: seeds the base
  `players`/`teams` tables and updates player ages.

> **A short (monthly) heap run against an empty `players` table silently
> inserts nothing.** At least one yearly dump must be present and processed
> *before* monthly dumps are useful. Always keep a yearly dump in the dump
> folder.

## Option 1 — CLI

From inside the running `backend` container (or the host `.venv` with the
env overrides described in [Configuration](Configuration.md)):

```bash
flask --app app init-db     # (re)creates the schema — destructive, drops existing tables
flask --app app update-db   # scans DUMP_PATH, ingests any new heaps, migrates, projects players
```

`init-db` only needs to be run once (or after a schema change). `update-db`
is safe to re-run — a `processed_heaps` table records which heaps have
already completed their migration/projection work, so `check_new_heaps()`
only returns heaps not yet recorded there. Run time scales with what's new
on disk, not with total dump history. See
[Ingestion Pipeline → §3](Ingestion-Pipeline.md#3-stage-1--discover-heaps-stagingpycheck_new_heaps)
for details.

To run from the host instead of inside the container, see the env-var
override example in [Configuration](Configuration.md).

## Option 2 — Admin API

The same two operations are also available as HTTP routes, which always run
inside the backend container with the correct config — no env overrides
needed. `update-db` runs as a background job you poll for status rather than
blocking the request. See [Admin API](Admin-API.md) for full request details.

```bash
curl -X POST http://localhost:5000/api/admin/init-db \
  -H "X-Admin-Token: $ADMIN_API_TOKEN"

curl -X POST http://localhost:5000/api/admin/update-db \
  -H "X-Admin-Token: $ADMIN_API_TOKEN"
# -> {"job_id": "..."}

curl http://localhost:5000/api/admin/jobs/<job_id> \
  -H "X-Admin-Token: $ADMIN_API_TOKEN"
```

## What happens during `update-db`

1. Every heap folder under `DUMP_PATH` not already recorded in
   `processed_heaps` is loaded into a raw staging database (unmodified OOTP
   schema).
2. A SQL migration runs from staging into the main app database:
   - Yearly heaps seed `players`/`teams` and update ages.
   - Monthly heaps add a dated rating snapshot per player.
3. For monthly heaps, expected stats/WAR are computed from the new ratings
   and inserted into the `*_expected` and `players_run_value` tables — this
   is what powers the projections and percentile views in the UI.

Both the CLI command and the Admin API job result carry the same summary:
how many heaps were processed, split into long vs. short counts.
