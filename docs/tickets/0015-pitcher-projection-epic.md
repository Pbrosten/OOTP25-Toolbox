# 0015 — Pitcher projections: schema, migration, and projection pipeline

- **Tag:** feat
- **Status:** Open
- **Depends on:** —
- **Blocks:** —

## 1. Problem

`staging.players_pitching` is already ingested every heap
(`DUMP_INCLUSION_LIST`, `backend/app/db/staging.py:8-15`) but nothing
downstream uses it: no `ootp` schema table, no migration SQL, no
`PitcherProjection` class analogous to `app/player_projection/BatterProjection`,
and no insertion into any `*_expected`/run-value table for pitchers. The
frontend's `PitcherPercentiles` component is a stubbed placeholder
(`docs/wiki/Features.md`) waiting on this backend work — batters already get
full expected-stat and run-value projections end to end, pitchers get
neither.

## 2. Design choices

This is the "finish the feature" alternative to
[0014](0014-drop-unused-pitching-ingestion.md)'s "stop the waste" chore —
see that ticket's Design choices section for the fork. This ticket is filed
as a large epic outline, not a fully-scoped implementation plan; treat the
Approach section below as a starting decomposition, to be broken into
per-subsystem tickets (schema, migration SQL, `PitcherProjection` class,
frontend wiring) the way the admin-API work was split into
[0001](0001-extract-db-service-layer.md)–[0006](0006-job-log-capture.md),
once/if this is prioritized.

- **Outstanding:** the actual pitching projection methodology (what stats to
  project, what run-value model to use for pitchers — analogous to
  `BatterProjection`'s wOBA/wRAA-based approach) is a domain/analytics
  design question not resolved by this ticket. It needs its own design pass
  before implementation starts, likely informed by whatever OOTP rating
  fields `staging.players_pitching` actually exposes (undocumented in this
  repo currently — would need inspecting a real dump export).

## 3. Approach (epic outline — needs further breakdown before implementation)

- Schema: add `ootp` tables mirroring the batting side —
  `players_pitching` (ratings snapshot per `rating_id`, FK to
  `players_rating`), `players_pitching_expected`, and a pitching
  contribution to run-value/WAR (either extend `players_run_value` or add a
  parallel table).
- Migration: extend `migration_short.sql` with `INSERT IGNORE` statements
  joining `players_rating`/`staging.players_pitching`, scoped to
  `r.rating_date = '{{HEAP_DATE}}'` from the start (don't repeat the mistake
  fixed in [0009](0009-scope-ratings-detail-inserts-to-heap-date.md)).
- Projection: new `app/player_projection/pitcher.py::PitcherProjection`
  class, methodology TBD (see Outstanding above); wire into
  `update.py::process_single_heap()`/`project_players()` alongside the
  existing batter pass.
- API: extend `app/api/projections.py` (or add a pitching-specific route) to
  serve pitcher projection data.
- Frontend: implement `PitcherPercentiles` against the new endpoint,
  replacing the current stub.
- Re-add `"players_pitching"` to `DUMP_INCLUSION_LIST` if
  [0014](0014-drop-unused-pitching-ingestion.md) shipped first.

**Files involved:**
- `backend/app/db/sql_scripts/schema.sql` (modified)
- `backend/app/db/sql_scripts/migration/migration_short.sql` (modified)
- `backend/app/player_projection/pitcher.py` (new)
- `backend/app/db/update.py`, `backend/app/db/projection.py` (modified)
- `backend/app/api/projections.py` (modified)
- `backend/app/db/staging.py` (modified, if 0014 shipped first)
- Frontend: `PitcherPercentiles` component (modified)
