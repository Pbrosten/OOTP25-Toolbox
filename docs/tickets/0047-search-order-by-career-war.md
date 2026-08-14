# 0047 — Order player search results by career WAR

- **Tag:** feat
- **Status:** Open
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
- **Outstanding — which pitching WAR column.** Pitching career stats carry
  two WAR figures, `war` and `ra9war` — two distinct methodologies passed
  through unmodified from OOTP's own export, per `migration_long.sql:97/107`.
  Defaulting to `war` for naming symmetry with the batting column is the
  obvious pick but isn't confirmed against what either column actually
  measures; not decided.
- **Outstanding — two-way players.** Summing both `players_career_batting_stats.war`
  and `players_career_pitching_stats.war` for a player who has rows in both
  is the simplest default, versus taking whichever total is larger or
  matches their listed position. Likely rare enough not to block a first
  pass; not decided.
- **NULL handling.** Players with no career-stat rows at all (pure prospects,
  or anyone [0046](0046-prune-inactive-players.md) hasn't yet excluded)
  should sort last, not error or sort first — `COALESCE`/treat missing WAR
  as 0.

## 3. Approach

- Extend the `/search` query with a per-player aggregated career WAR — a
  subquery/CTE summing `players_career_batting_stats.war` and
  `players_career_pitching_stats.war` grouped by `player_id`, left-joined
  onto the existing name-match query — and add `ORDER BY` that total
  descending, keeping the existing `LIKE` filter and `LIMIT 10`.

**Files involved:**
- `backend/app/api/players.py` (modified)
