# 0027 — Pitcher projections API route + `PitcherPercentiles` component

- **Tag:** feat
- **Status:** Open
- **Depends on:** [0026](0026-pitcher-projection-methodology.md)
- **Blocks:** —

## 1. Problem

`PlayerProfile.vue` already branches on `position === 'P'`
(`frontend/src/views/PlayerProfile.vue:33-35`) to render `PitcherPercentiles`,
but the import is commented out and the component is a local `const
PitcherPercentiles = {}` stand-in (`frontend/src/views/PlayerProfile.vue:6,17`).
There's no backend route to feed it either — `app/api/projections.py` only
has `/expected/batting`, `/expected/basepath`, `/expected/fielding`, and
`/expected/value/percentiles` (all batting-side).

## 2. Design choices

- **New routes vs. extending existing ones.** The batting percentile routes
  are stat-family-scoped (`/expected/batting/percentiles`,
  `/expected/fielding/percentiles`, ...) rather than one generic endpoint.
  **Chosen:** follow the same pattern — add
  `/<int:rating_id>/expected/pitching/percentiles` (and a plain
  `/expected/pitching`/`/<rating_id>/expected/pitching` pair mirroring the
  batting routes' shape) rather than overloading the batting routes with a
  player-type branch, for consistency with the existing blueprint.
- **Percentile population.** The batting percentile routes compare a
  player's expected stats against the full `players_batting_expected`
  population (see `get_expected_batting_percentiles`,
  `backend/app/api/projections.py:61-95`, for the exact query shape). The
  pitching route should compare against `players_pitching_expected` the same
  way — no new design question here, just needs 0026's table to exist first.
- **Outstanding:** exact response shape depends entirely on what 0026's
  `players_pitching_expected` columns turn out to be.

## 3. Approach

- `backend/app/api/projections.py`: add routes mirroring
  `get_expected_batting_stats` / `get_expected_batting_stats_by_id` /
  `get_expected_batting_percentiles` (lines 13-95), reading from
  `players_pitching_expected` (and the pitching run-value table from 0026)
  instead of the batting tables.
- `backend/docs/openai.yaml`: document the new routes, per this repo's
  standing convention of keeping the OpenAPI spec in sync.
- `frontend/src/components/percentiles/PitcherPercentiles.vue` (new):
  mirror `BatterPercentiles.vue`'s structure (fetch by `playerId`, render
  percentile bars) against the new endpoint.
- `frontend/src/views/PlayerProfile.vue`: uncomment the real import
  (line 6), delete the `const PitcherPercentiles = {}` stand-in (line 17).
- `docs/wiki/Features.md`: remove the "stubbed out" note once shipped.

**Files involved:**
- `backend/app/api/projections.py` (modified)
- `backend/docs/openai.yaml` (modified)
- `frontend/src/components/percentiles/PitcherPercentiles.vue` (new)
- `frontend/src/views/PlayerProfile.vue` (modified)
- `docs/wiki/Features.md` (modified)
