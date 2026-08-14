# 0047 — Order player search results by career WAR

- **Tag:** feat
- **Status:** Closed
- **Depends on:** —
- **Blocks:** —

## 1. Problem

`app/api/players.py`'s `/search` route (lines 59-88) matches players by name
(`LIKE`) and returns the first 10 rows with no `ORDER BY` at all — result
order is whatever the database happens to produce (effectively primary-key/
insertion order), truncated to 10. For any name shared by multiple players
across a save's full history, the most relevant player (the one an MLB-focused
GM actually means) has no priority over an obscure short-career player who
happens to share the name, and can easily fall outside the top-10 cutoff.

## 2. Design choices

- **Metric: sum of career WAR.** Both `players_career_batting_stats.war` and
  `players_career_pitching_stats.war` (and `ra9war`) are already ingested per
  season row (`migration_long.sql:48-162`) — summing across a player's rows
  gives a single career-WAR figure with no new ingestion needed, acting as a
  "fame weight" so established players outrank marginal ones sharing a name.
- **Resolved (user decision) — pitching WAR column: `war`, not `ra9war`.**
  Asked directly. `war` is the FIP/component-based, defense-neutral figure
  (matches naming symmetry with the batting side); `ra9war` is runs-allowed-
  based, including defense/luck. Chose `war`.
- **Resolved (user decision) — two-way players: `MAX(batting, pitching)`,
  not `SUM`.** Asked directly, with real data to inform the choice: 6,001 of
  the roughly 16-22k players with any career stats have rows in **both**
  `players_career_batting_stats` and `players_career_pitching_stats` — far
  from the "likely rare" assumption originally written here. Checked who:
  almost entirely pitchers with small/negative incidental batting WAR from
  an era before universal DH (e.g. Clayton Kershaw: -4.1 batting / +91.5
  pitching), plus rare genuine two-way players (Shohei Ohtani: +34.9
  batting / +21.0 pitching). Chose `MAX` over `SUM` — ranks by whichever
  half of a player's career actually carries their value, rather than
  letting a negative incidental-batting figure drag down (or a positive one
  inflate) a primarily-pitching (or -batting) player's rank.
- **NULL handling.** Players with no career-stat rows at all (pure prospects,
  or anyone [0046](0046-prune-inactive-players.md) hasn't yet excluded)
  should sort last, not error or sort first — `COALESCE`/treat missing WAR
  as 0.

## 3. Approach

- Extended the `/search` query in `app/api/players.py` with two LEFT-JOINed
  per-player aggregate subqueries (`SUM(war) GROUP BY player_id`, one each
  for `players_career_batting_stats`/`players_career_pitching_stats`), and
  an `ORDER BY` `CASE` expression implementing the `MAX(batting, pitching)`
  decision with the NULL-handling from the Design choices (both missing →
  0; only one present → that one; both present → `GREATEST`). Moved
  `LIMIT 10` into the SQL itself (previously a Python `players[:10]` slice
  after fetching every match) since sorting has to happen before truncating.
- **Verified against real data** (the dev database populated by
  [0046](0046-prune-inactive-players.md)'s update-db run): `GET
  /api/players/search?q=Rodriguez` now returns Julio Rodriguez (real,
  currently-rostered Mariners CF) first, followed by other real
  currently-active MLB players, instead of the previous player_id-ordered
  list of obscure free agents. Confirmed a zero-career-stats prospect
  (`player_id=48372`, the same DSL player used to verify
  [0045](0045-remove-mlb-percentile-toggle.md)) sorts near the bottom
  rather than erroring or sorting first. A broad single-letter query
  (`q=a`, matching a large share of the table) completed in ~112ms — no
  meaningful performance concern from the added joins. Backend container
  needed a manual restart to pick up the code change (no `--reload` in
  `Dockerfile.dev`'s `CMD ["flask", "run"]`).
- **Found but not fixed: `tests/api/test_players.py` has 11 pre-existing
  failures, unrelated to this change.** All fail identically with this
  change stashed out (confirmed via `git stash`/`git stash pop`), including
  tests for routes this ticket never touched (`test_get_players`,
  `test_get_player_ratings_*`). Root cause looks like a mock/implementation
  mismatch: the tests set `mock_con.execute.return_value = mock_cursor`,
  but the actual routes call `with con.cursor() as cursor:` — the mocked
  connection's `.cursor()` was never wired up, so the context manager
  yields an unconfigured `MagicMock` instead. Out of scope here; flagging
  in case a cleanup ticket is wanted.

**Files involved:**
- `backend/app/api/players.py` (modified)
