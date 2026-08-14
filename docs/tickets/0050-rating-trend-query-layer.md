# 0050 — Rating delta/trend query layer + API route

- **Tag:** feat
- **Status:** Closed
- **Depends on:** —
- **Blocks:** [0051](0051-development-alert-generation.md), [0052](0052-development-monitor-frontend.md)

## 1. Problem

[0044](0044-player-development-monitor.md) (Player Development Monitor) needs
a way to detect meaningful rating changes per player across heaps. Nothing
today reads `players_rating` across snapshots — every existing consumer
(`PercentileBar.vue`, `BatterPercentiles.vue`, `PitcherPercentiles.vue`) only
looks at the latest rating for a player. This ticket builds the read-only
query layer that computes per-category deltas; it does not generate
human-readable alerts (that's [0051](0051-development-alert-generation.md))
or render anything (that's [0052](0052-development-monitor-frontend.md)).

## 2. Design choices

0044 resolved the product-level questions this ticket implements:

- **Comparison window: sliding 3-heap lookback.** Each heap's snapshot is
  compared to the snapshot from 3 heaps prior for that same player,
  re-evaluated every heap — not a single previous-heap diff, and not an
  average-of-windows comparison. Heaps aren't evenly spaced per player
  (players can be absent from a heap — free agents, retired-and-filtered
  players per [0046](0046-prune-inactive-players.md) — so "3 heaps back" is
  computed via each player's own row sequence over `players_rating`, not a
  fixed calendar offset (`DATE_SUB(rating_date, INTERVAL 3 MONTH)` would
  under/over-count whenever a heap is missing for that player).
- **Thresholds: 5-point delta for "overall" ratings, 10-point delta for
  "talent" (potential) ratings.** Grounded in real `ootp` data (checked via
  `players_batting.contact/power` and `players_pitching.stuff` heap-to-heap
  diffs): rating values only ever move in steps of 5 on this scale; ~97% of
  player/category/heap comparisons show 0 change, ~2.7% show a single
  5-point move (routine monthly drift), and 10+-point single-heap jumps are
  rare (~0.01–0.1% of comparisons). Both "overall" (current-ability) and
  "talent" (potential/ceiling) tables are in scope per 0044's resolution,
  each with its own flat threshold.
- **Resolved — which tables are in scope.** Overall: `players_batting`,
  `players_pitching`, `players_fielding`, `players_basepath`,
  `players_fielding_position`. Talent: `players_batting_talent`,
  `players_pitching_talent`, `players_fielding_position_talent` (there is no
  `players_fielding_talent` or `players_basepath_talent` — those categories
  only have an "overall" table in the schema). All columns in each table are
  numeric ratings except `players_pitching.role` (a role code, not a rating)
  and every table's `rating_id` — both excluded from delta computation.
- **Resolved — sequencing player heaps.** Use `ROW_NUMBER() OVER (PARTITION
  BY player_id ORDER BY rating_date)` on `players_rating` to assign each
  player their own heap sequence, then self-join a row to the row 3 sequence
  numbers earlier for the same player. A player with fewer than 4 recorded
  heaps has no "3 heaps back" row and simply produces no trend result yet
  (not an error condition).
- **Resolved — response shape.** One route,
  `GET /api/players/ratings/<int:player_id>/trends`, returns every delta
  across all 8 in-scope tables for the player's latest heap vs. 3 heaps
  back — not just the ones exceeding threshold — since 0052 needs the full
  per-category delta for a sparkline/trend display, while 0051 only needs
  the subset where `exceeded` is true. Filtering "only exceeded" belongs to
  the alert layer, not this query.

## 3. Approach

- New SQL script `backend/app/db/sql_scripts/api/get_player_rating_trends.sql`:
  a CTE (`sequenced`) numbering each player's `players_rating` rows by
  `rating_date`, then one `UNION ALL` branch per in-scope table joining the
  latest sequenced row to the row 3 back, selecting `table_name` (literal),
  `column` is not expressible per-column in one SQL statement cleanly across
  differently-shaped tables — instead each table contributes one row per
  rating column via explicit column selection (8 tables × their own column
  lists, matching the pattern already used for percentile queries like
  `get_player_expected_pitching_percentiles.sql`'s multi-CTE shape), with a
  literal `threshold` column (5 or 10) and `exceeded` computed in SQL
  (`ABS(current - prior) >= threshold`).
- `backend/app/api/ratings.py`: add `get_player_rating_trends(player_id)`
  handler mirroring the existing `get_db()`/`try`/`close_db()` pattern,
  loading the SQL file via `current_app.open_resource(...)` like the
  non-trivial queries in `app/api/projections.py`. 404s if the player has no
  `players_rating` rows at all; returns an empty list (not 404) if the
  player exists but has fewer than 4 heaps.
- `backend/docs/openai.yaml`: document the new route and its response schema
  (list of `{table, column, from_date, to_date, from_value, to_value, delta,
  threshold, exceeded}` objects).

**Verified:** full pytest suite (86 passed, no regressions); ran the raw SQL
directly against the live `ootp` database for a real player with 60 recorded
heaps — confirmed exactly 67 rows returned (one per in-scope rating column),
correct `exceeded` flag (one true positive: `players_pitching.hold` moved
40 -> 45, a 5-point delta at the overall threshold), and correct `from_date`/
`to_date` (heap 3 back vs. latest heap). Hit the live route end-to-end after
restarting the backend container (its `flask run` predated this session's
changes and wasn't running with the reloader, same gotcha noted in 0027's
Verified section) — `GET /api/players/ratings/5/trends` returns 200 with 67
rows, `GET /api/players/ratings/999999999/trends` returns 404. One fix
needed during implementation: `to_date` collides with a MariaDB Oracle-mode
reserved word (`TO_DATE()`) and needed backtick-quoting in the first UNION
branch's column alias (MariaDB doesn't require repeating aliases in later
UNION ALL branches, so this was a single fix, not 67).

**Files involved:**
- `backend/app/db/sql_scripts/api/get_player_rating_trends.sql` (new)
- `backend/app/api/ratings.py` (modified)
- `backend/docs/openai.yaml` (modified)
