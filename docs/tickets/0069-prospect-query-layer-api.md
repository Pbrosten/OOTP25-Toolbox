# 0069 — Prospect query layer + API route

- **Tag:** feat
- **Status:** Open
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
- `backend/app/api/players.py` or `backend/app/api/prospects.py` (new
  route)
- `backend/docs/openai.yaml` (modified)
- `backend/tests/api/test_prospects.py` (new)
