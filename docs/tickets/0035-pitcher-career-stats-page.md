# 0035 — Pitcher career stats table (mirror batter career stats)

- **Tag:** feat
- **Status:** Open
- **Depends on:** —
- **Blocks:** —

## 1. Problem

`PlayerDetails.vue`'s "Career Batting Stats" table
(`frontend/src/components/PlayerDetails.vue:162-235`) only renders when
`playerDetails.position !== 'P'`. Pitchers get no equivalent — there is no
`players_career_pitching_stats` table anywhere in `schema.sql`, no such table
in `staging.DUMP_INCLUSION_LIST` (`backend/app/db/staging.py:9-16`), no
migration insert, and no API route. Grepping the whole backend/frontend for
`career_pitching`/`career/pitching` turns up nothing — this is not a bug in
an existing feature, it's a feature that was never built.

The existing pitcher-side profile pieces don't fill this gap: `PitcherPercentiles`
(0027) shows population-percentile bars for *projected* value (WAR, ERA/xBA/xwOBA,
ratings), and `PitchRepertoire` (0033) shows current pitch grades — neither is a
season-by-season table of actual career box-score stats. The reference screenshot
(a real per-season pitching line: `W L ERA G GS SV IP SO WHIP`, plus a bold
"N Seasons" totals row) is exactly what `players_career_batting_stats` +
`PlayerDetails.vue`'s batting table already provide for hitters — this ticket
is that same pattern, mirrored to pitching.

## 2. Design choices

- **Source table & column names.** OOTP's dump almost certainly exports a
  `players_career_pitching_stats` staging table parallel to
  `players_career_batting_stats`, but its exact column names/types (e.g. is
  `ip` stored as a decimal with thirds, or as an outs-count integer; are
  `w`/`l`/`sv`/`so`/`bb`/`h`/`er`/`g`/`gs` present directly) are not
  verifiable from this repo — no sample dump is checked in. **Outstanding:**
  before writing `schema.sql`, inspect a real dump's
  `staging.players_career_pitching_stats` (same method [0024](0024-pitcher-schema-ratings-tables.md)
  used for `players_pitching`'s ratings columns — a `TEST.lg`-style save,
  yearly heap) rather than guessing at column names.
- **Rate stats computed client-side vs. stored.** `players_career_batting_stats`
  only stores counting stats; AVG/OBP/SLG/OPS are computed in
  `PlayerDetails.vue` from those counts (established, and later fixed, by
  [0023](0023-fix-career-batting-rate-stats-display.md)). **Chosen:** same
  pattern here — store raw counting stats only (`ip`, `er`, `bb`, `h`, `so`,
  `w`, `l`, `sv`, `g`, `gs`, ...), compute `ERA = 9 * er / ip` and
  `WHIP = (bb + h) / ip` client-side, guarding both against `ip === 0` the
  same way the batting table guards AVG/SLG against `ab === 0` — avoids a
  second source of truth for derived rate stats.
- **MLB/MiLB split.** The batting route (`get_player_career_batting`,
  `backend/app/api/players.py:132`) checks for any `league_id = 203` row for
  the player and picks between `get_player_career_batting_mlb.sql` /
  `_milb.sql` accordingly. **Chosen:** mirror this exactly — new
  `GET /api/players/<player_id>/career/pitching` route with the same
  detection query and a parallel `get_player_career_pitching_mlb.sql` /
  `_milb.sql` pair.
- **Where the table renders.** **Chosen:** inside `PlayerDetails.vue`,
  gated on `playerDetails.position === 'P'` (the inverse of the existing
  batting guard), rendered alongside — not replacing — `PitcherPercentiles`
  and `PitchRepertoire`, which live in `PlayerProfile.vue`, not
  `PlayerDetails.vue`. No component reshuffling needed: `PlayerDetails.vue`
  already renders nothing extra for pitchers today, so this just fills that
  gap in place.
- **Column set / layout.** Matches the reference screenshot: `Year, Team, W,
  L, ERA, G, GS, SV, IP, SO, WHIP`, with a bold "N Seasons" totals row.
  **Chosen:** follow the batting table's responsive pattern (`hidden
  lg:table-cell` / `hidden sm:table-cell` on lower-priority columns) rather
  than inventing a new layout convention.

## 3. Approach

- `backend/app/db/staging.py`: add `"players_career_pitching_stats"` to
  `DUMP_INCLUSION_LIST`.
- `backend/app/db/sql_scripts/schema.sql`: add `players_career_pitching_stats`
  (columns per the dump-inspection outcome above; expected shape —
  `player_id, year, team_id, game_id, league_id, level_id, split_id, w, l,
  sv, g, gs, ip, h, er, bb, so, hr, ...`, `PRIMARY KEY (player_id, year,
  team_id)`, `FOREIGN KEY (player_id) REFERENCES players(player_id)`,
  `FOREIGN KEY (team_id) REFERENCES teams(team_id)`, matching
  `players_career_batting_stats`'s shape at `schema.sql:71-108`) plus the
  matching `DROP TABLE IF EXISTS` line.
- `backend/app/db/sql_scripts/migration/migration_long.sql`: add an
  `INSERT INTO players_career_pitching_stats ... FROM
  staging.players_career_pitching_stats s INNER JOIN players p ON
  s.player_id = p.player_id WHERE s.split_id = 1 ON DUPLICATE KEY UPDATE
  ...`, mirroring the batting insert at `migration_long.sql:48-69`.
- `backend/app/db/sql_scripts/api/get_player_career_pitching_mlb.sql` (new)
  and `get_player_career_pitching_milb.sql` (new): mirror
  `get_player_career_batting_mlb.sql` / `_milb.sql`'s per-year/team
  aggregation shape, selecting the new counting-stat columns.
- `backend/app/api/players.py`: add `GET
  /<int:player_id>/career/pitching`, mirroring `get_player_career_batting`
  (`players.py:130-169`) — same MLB-presence check, same
  `sql_file`-selection branch, same 404-on-empty behavior.
- `backend/docs/openai.yaml`: document the new route + a
  `PitchingCareerStats`-style schema (note the batting equivalent isn't
  documented either — pre-existing gap, not required here, but the new
  route should be documented going forward per this project's convention
  for new endpoints).
- `frontend/src/components/PlayerDetails.vue`: add a "Career Pitching
  Stats" table gated on `playerDetails.position === 'P'`, fetched from the
  new route in the existing `onMounted` `Promise.all`, with `calcEra`/
  `calcWhip` helpers (returning `null` on `ip === 0`, formatted via a
  ERA/WHIP-appropriate variant of `formatRate` — unlike AVG/OBP/SLG, ERA and
  WHIP are conventionally displayed with a leading digit, e.g. `3.60`, not
  `.360`, so this is *not* the same `formatRate` used for batting rates),
  same responsive/totals-row structure as the batting table.
- Manually verify against a real pitcher profile in the running app (no
  sample dump in-repo to drive an automated test, same constraint 0033
  flagged for its own frontend piece).

**Files involved:**
- `backend/app/db/staging.py` (modified)
- `backend/app/db/sql_scripts/schema.sql` (modified)
- `backend/app/db/sql_scripts/migration/migration_long.sql` (modified)
- `backend/app/db/sql_scripts/api/get_player_career_pitching_mlb.sql` (new)
- `backend/app/db/sql_scripts/api/get_player_career_pitching_milb.sql` (new)
- `backend/app/api/players.py` (modified)
- `backend/docs/openai.yaml` (modified)
- `frontend/src/components/PlayerDetails.vue` (modified)
