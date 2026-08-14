# 0027 — Pitcher projections API route + `PitcherPercentiles` component

- **Tag:** feat
- **Status:** Closed
- **Depends on:** [0026](0026-pitcher-projection-methodology.md), [0028](0028-pitcher-run-value-war.md)
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
- **Resolved:** response shape. Rather than a separate value-percentiles
  route mirroring the batting side's standalone `/expected/value/percentiles`,
  `players_pitching_expected` and `players_pitching_run_value` are joined
  in a single `get_player_expected_pitching_percentiles.sql` query — one
  route, one fetch on the frontend — since pitchers only have these two
  backing tables (no basepath/fielding equivalents: fielding is always zero
  per 0028, pitchers don't steal bases). Fields returned: `pitching_runs`,
  `baserunning_runs`, `total_runs`, `war` (from `players_pitching_run_value`,
  all higher-is-better); `era`, `xba`, `xwoba` (from
  `players_pitching_expected`, all **lower**-is-better — comparisons
  inverted, `WHERE stat > target.stat` instead of `<`); `stuff`, `control`,
  `pbabip`, `hra`, `stamina`, `hold` (from `players_pitching` ratings, all
  higher-is-better, same direction as batting ratings). Cohort filter is
  `p.position = 'P'` (inverse of the batting query's `!= 'P'`), otherwise
  identical to `get_player_expected_batting_percentiles.sql`'s shape — no
  SP/RP split, matching this ticket's own stated non-decision on cohort
  scoping.

## 3. Approach

- `backend/app/api/projections.py`: added `get_expected_pitching_stats` /
  `get_expected_pitching_stats_by_id` / `get_expected_pitching_percentiles`,
  structural mirrors of the batting routes, reading from
  `players_pitching_expected` and (percentiles route only) the new SQL file
  below.
- `get_player_expected_pitching_percentiles.sql` (new): see Design choices
  above for the exact shape — three CTEs (`expected_filtered`,
  `ratings_filtered`, `value_filtered`), one per source table.
- `backend/docs/openai.yaml`: added `/api/players/stats/expected/pitching`
  and `/{rating_id}` entries plus a `PitchingExpected` schema, mirroring the
  existing `BattingExpected` entries. Percentile routes remain undocumented
  here, matching the pre-existing gap for batting/basepath/fielding/value
  percentiles (not this ticket's scope to fix).
- `frontend/src/components/percentiles/PitcherPercentiles.vue` (new):
  mirrors `BatterPercentiles.vue`'s structure (year selector, MLB/current
  toggle, `PercentileBar` rows) but simpler — one fetch instead of four,
  since the one combined percentiles endpoint covers both "Value" and
  "Pitching" sections.
- `frontend/src/views/PlayerProfile.vue`: uncommented the real import,
  deleted the `const PitcherPercentiles = {}` stand-in, passed `leagueId`
  through (the stand-in usage was missing it).
- `docs/wiki/Features.md` / `docs/wiki/Projections.md`: removed the
  "stubbed out" note, documented the new section and its endpoint.

**Verified:** full pytest suite (same 11 pre-existing, unrelated failures);
live end-to-end run seeding an isolated throwaway database (3 pitchers + 1
batter) through the real `fetch → project → insert` path, then hitting all
three new HTTP routes and hand-verifying the percentile math (including the
inverted ERA/xBA/xwOBA direction and the `position = 'P'` cohort filter
correctly 404ing a batter's rating_id); confirmed against the real, live
`ootp` database (427,439 populated `players_pitching_expected` rows) after
restarting the backend container (its `flask run` process predated this
session's code changes and wasn't running with the reloader, so the
bind-mounted source updates weren't picked up until restart) — real pitcher
profile pages now load percentiles correctly end-to-end.

**Files involved:**
- `backend/app/api/projections.py` (modified)
- `backend/app/db/sql_scripts/api/get_player_expected_pitching_percentiles.sql` (new)
- `backend/docs/openai.yaml` (modified)
- `frontend/src/components/percentiles/PitcherPercentiles.vue` (new)
- `frontend/src/views/PlayerProfile.vue` (modified)
- `docs/wiki/Features.md`, `docs/wiki/Projections.md` (modified)
