# OOTP25-Toolbox Wiki

A user-facing guide to installing, configuring, and using OOTP25-Toolbox — a
Flask + Vue app that parses OOTP Baseball 25 MySQL dump exports into
analytics and projections (player search, batter projections, run-value
estimates, percentile profiles), backed by MariaDB.

This wiki mostly covers *using* the app; one page ([Ingestion Pipeline](Ingestion-Pipeline.md))
goes deep on backend internals for contributors. For repo-wide conventions
(backend/frontend structure, ticket process), see
[CLAUDE.md](../../CLAUDE.md) at the repo root.

## Pages

1. [Installation](Installation.md) — prerequisites, cloning, first-time setup.
2. [Configuration](Configuration.md) — `.env` variables, dump file paths,
   `docker-compose.yml` volume mounts.
3. [Updating the Database](Updating-the-Database.md) — configuring OOTP to
   export dump files, and ingesting them via the CLI or Admin API.
4. [Admin API](Admin-API.md) — the `/api/admin` endpoints for triggering
   `init-db`/`update-db` over HTTP instead of the CLI.
5. [Features](Features.md) — a tour of what the app UI does: player search,
   player profiles, batter projections, and percentile comparisons.
6. [Ingestion Pipeline](Ingestion-Pipeline.md) — developer reference:
   exactly what `update-db` does stage by stage, current limitations, and
   test coverage status. Pairs with
   [docs/improvements](../improvements/README.md), a list of concrete
   improvement recommendations from a full pipeline review.
7. [Projections](Projections.md) — developer reference: how ratings become
   expected stats, for both the implemented batter methodology and the
   spreadsheet-only (not yet implemented) pitcher methodology.
8. [Troubleshooting](Troubleshooting.md) — fixes for the most common setup
   problems.

## Quick start

```bash
# 1. Copy backend/templates/.env-template -> backend/.env and fill it in
#    (see Configuration.md)

# 2. Bring up the stack
podman compose up -d      # or: docker-compose up --build

# 3. Load your OOTP dump files into the database
#    (see Updating the Database.md)

# 4. Open the app
#    Frontend: http://localhost:5173
#    Backend:  http://localhost:5000
```
