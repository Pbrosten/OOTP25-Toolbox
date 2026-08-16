# 0069 — Prospect query layer + API route

- **Tag:** feat
- **Status:** Closed
- **Depends on:** [0068](0068-prospect-fv-value-calculation.md)
- **Blocks:** [0070](0070-prospect-pipeline-frontend.md)

## 1. Problem

[0043](0043-prospect-pipeline.md)'s prospect definition, org-depth reuse,
and trend reuse are all resolved (see 0043's Design choices), and
[0068](0068-prospect-fv-value-calculation.md) provides the per-player
FV/value/readiness calculation. Nothing yet identifies *which* players are
prospects, or exposes any of this over the API for a frontend to consume.

## 2. Design choices

Resolved in 0043 — implementation-level restatement:

- **Prospect definition (query filter):** `teams.level != 1` OR
  (`teams.level = 1` AND `players_service_time.mlb_service_years = 0`),
  joined the same way [0063](0063-roster-depth-chart-query-api.md)'s org
  query already joins `players` → `teams`.
  - **Post-close correction (user report, verified live via
    `/teams/21/prospects` -- Philadelphia):** level/service-time alone let
    a veteran journeyman briefly optioned back to AAA/A show up as a
    "prospect" -- real case, Zach Pop, age 32, level 3 (AA). Added `p.age
    < 26` as an additional filter in `get_prospects.sql`'s `prospects` CTE
    (on top of, not instead of, the level/service-time check). No schema/
    API contract change -- same response shape, just a narrower row set.
- **Organizational depth at position:** reuse
  `get_org_depth_chart.sql` (0063) rather than a parallel query — this
  ticket's own SQL only needs to add the prospect-definition filter and
  0068's calc output on top, not reimplement org/level grouping.
- **Development trajectory:** reuse 0050's rating-trend query
  (`app/api/ratings.py` / its trend SQL script) per player, not
  reimplemented here.
- **FV/value/readiness:** call into 0068's `calculate_prospect_value` per
  candidate player. Given the FV/value calc runs `BatterProjection`/
  `PitcherProjection` twice per player (talent + current), scope this to
  the already-filtered prospect set from the query above, not the full
  player table.

## 3. Approach

- New SQL, `backend/app/db/sql_scripts/api/get_prospects.sql`: base
  prospect-eligible player set (definition above) with position, age,
  current level, org (`team_id`/`parent_team_id`), latest `rating_id`, and
  whatever raw rating columns 0068's calc needs to build its talent/current
  hybrid input (avoids N+1 queries — pull everything in one pass, similar
  to how existing percentile endpoints join wide).
- Route in `app/api/players.py` (or a new `app/api/prospects.py` if the
  existing blueprints are getting crowded — match whichever the codebase's
  current blueprint size suggests), e.g. `GET /api/prospects` with
  position/level/org filters, calling 0068's module per row and merging in
  0050's trend output per player.
- Response shape: one row per prospect — identity (name, age, position,
  level, org), FV grade, expected surplus value/WAR/star odds (or "not
  available"), MLB-promotion-ready flag (or omitted when not at a
  sub-MLB level), and trend direction from 0050.
- Update `backend/docs/openai.yaml` per CLAUDE.md's API-doc convention.

**Files involved:**
- `backend/app/db/sql_scripts/api/get_prospects.sql` (new)
- `backend/app/api/prospects.py` (new route, new blueprint -- kept separate
  from `players.py` rather than extending it, matching this ticket's own
  "or a new file if crowded" option: `players.py` was already 400 lines)
- `backend/app/__init__.py` (registers the new blueprint)
- `backend/docs/openai.yaml` (modified)
- `backend/tests/api/test_prospects.py` (new)
- `backend/app/player_projection/prospect_value.py`,
  `app/player_projection/development_alerts.py` (reused, unmodified)

## 4. Verified against real data (`TEST.lg` save, post-0067)

- `GET /api/prospects?team_id=<a real org>` (214 prospects for one org):
  ~1.6s, all fields populated as expected (FV/surplus-value/star-odds,
  `mlb_promotion_ready` present only at `level != 1`, trend direction
  correctly derived from 0051's alerts).
- `GET /api/prospects` unfiltered (6,395 league-wide prospects across this
  save's 259 teams): ~46s. Expected, not a regression — this ticket's own
  Design choices already accepted the N+1-per-prospect cost (talent +
  current projection, twice, plus a trend query, per player) as the
  tradeoff for not building a bulk/batched variant. The `team_id` filter
  exists precisely so a real caller (0070's frontend, inherently org-
  scoped) never has to pay the unfiltered cost. Not treated as a blocker;
  worth revisiting if a future consumer needs the unfiltered list to be
  fast.
- **Found via the real run, not a bug:** 2 of 6,395 players (`RF`/`SS`
  positions, both `level = 6`) have *no* `players_batting`/
  `players_batting_talent` row at all at their latest heap (confirmed
  across their 6 most recent heaps, not a one-off gap) — a real, pre-
  existing sparse-data case, not introduced by this ticket's query. The
  calc module's `KeyError` on the `None` rating is caught by
  `_value_for`'s try/except (mirrors `app/db/projection.py`'s
  `process_player`/`process_pitcher` precedent) and surfaces correctly as
  `{"available": false}` with a logged warning, rather than crashing the
  whole request. No fix needed here; root cause is upstream data
  sparsity, out of this ticket's scope.
