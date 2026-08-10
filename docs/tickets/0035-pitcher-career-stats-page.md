# 0035 — Pitcher career stats table (mirror batter career stats)

- **Tag:** feat
- **Status:** Closed
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

- **Source table & column names — resolved.** Inspected the real `TEST.lg`
  save's 2029 yearly heap
  (`dump_2029_yearly/mysql/players_career_pitching_stats.mysql.sql`) directly,
  same method [0024](0024-pitcher-schema-ratings-tables.md) used for
  `players_pitching`. 58 columns: `player_id, year, team_id, game_id,
  league_id, level_id, split_id, ip, ab, tb, ha, k, bf, rs, bb, r, er, gb, fb,
  pi, ipf, g, gs, w, l, s, sa, da, sh, sf, ta, hra, bk, ci, iw, wp, hp, gf, dp,
  qs, svo, bs, ra, cg, sho, sb, cs, hld, ir, irs, wpa, li, stint, outs, sd,
  md, war, ra9war` (no `position` column, unlike the batting source table).
  Confirmed by cross-checking real rows: `outs` is the exact recorded-outs
  count (e.g. `outs=534` for a 31-start season) and `ip` is the same value
  pre-divided-and-floored to whole innings (`floor(534/3) = 178 = ip`) — so
  `ip` silently drops the `.1`/`.2` thirds OOTP conventionally displays,
  while `outs` doesn't. `s` is saves, not shutouts (`sho` is separate) —
  confirmed against a real closer row (`g=64, gs=0, gf=58, s=30, svo=42`).
  `k` is strikeouts (this table's name for what the screenshot calls `SO`),
  `ha` is hits allowed, `hra` is home runs allowed (a count here, unlike
  `players_pitching.hra`'s 20-80 *rating* — same column name, different
  table, different meaning).
- **Full mirror vs. trimmed column set.** `players_career_batting_stats`
  (`schema.sql:71-108`) mirrors its staging source almost 1:1 (drops only
  `position`), even though several of its columns
  (`pitches_seen`, `gdp`, `ci`, `wpa`, `ubr`, ...) aren't read by any current
  query — unlike [0024](0024-pitcher-schema-ratings-tables.md)'s ratings
  tables, which were deliberately trimmed to only what a consumer needed.
  **Chosen:** follow the career-stats precedent, not the ratings-table one —
  mirror all 58 columns into `players_career_pitching_stats` unchanged. Two
  tables in the same "career box-score stats" family should follow the same
  convention; trimming here would just mean another migration later if a
  future ticket wants e.g. `hld`/`qs`/`ra9war`.
- **Rate stats computed client-side vs. stored.** `players_career_batting_stats`
  only stores counting stats; AVG/OBP/SLG/OPS are computed in
  `PlayerDetails.vue` from those counts (established, and later fixed, by
  [0023](0023-fix-career-batting-rate-stats-display.md)). **Chosen:** same
  pattern here — store raw counting stats only, compute
  `IP_display = floor(outs/3) + '.' + (outs % 3)` (OOTP's thirds notation,
  using `outs` not the lossy `ip` column per the resolved question above),
  `ERA = 9 * er / (outs/3)`, and `WHIP = (bb + ha) / (outs/3)` client-side,
  guarding all three against `outs === 0` the same way the batting table
  guards AVG/SLG against `ab === 0`.
- **MLB/MiLB split.** The batting route (`get_player_career_batting`,
  `backend/app/api/players.py:132`) checks for any `league_id = 203` row for
  the player and picks between `get_player_career_batting_mlb.sql` /
  `_milb.sql` accordingly. **Chosen:** mirror this exactly — new
  `GET /api/players/<player_id>/career/pitching` route with the same
  detection query and a parallel `get_player_career_pitching_mlb.sql` /
  `_milb.sql` pair.
- **Where the table renders — user-specified layout.** **Chosen:** inside
  `PlayerDetails.vue`, gated on `playerDetails.position === 'P'` (the
  inverse of the existing batting guard) — so it renders directly under the
  player-info header, in the same "player info" column as the reference
  screenshot shows. `PitchRepertoire` moves to render directly below it in
  that same column (currently it's stacked with `PitcherPercentiles` in
  `PlayerProfile.vue`'s right-hand column instead — see Approach for the
  exact restructuring). `PitcherPercentiles` stays alone in the right-hand
  column.
- **Column set / layout.** Matches the reference screenshot: `Year, Team, W,
  L, ERA, G, GS, SV, IP, SO, WHIP`, with a bold "N Seasons" totals row.
  **Chosen:** follow the batting table's responsive pattern (`hidden
  lg:table-cell` / `hidden sm:table-cell` on lower-priority columns) rather
  than inventing a new layout convention.

## 3. Approach

- `backend/app/db/staging.py`: add `"players_career_pitching_stats"` to
  `DUMP_INCLUSION_LIST`.
- `backend/app/db/sql_scripts/schema.sql`: add `players_career_pitching_stats`
  with all 58 columns from the resolved source shape above,
  `PRIMARY KEY (player_id, year, team_id)`,
  `FOREIGN KEY (player_id) REFERENCES players(player_id)`,
  `FOREIGN KEY (team_id) REFERENCES teams(team_id)` — same key shape as
  `players_career_batting_stats` (`schema.sql:71-108`) — plus the matching
  `DROP TABLE IF EXISTS` line.
- `backend/app/db/sql_scripts/migration/migration_long.sql`: add an
  `INSERT INTO players_career_pitching_stats ... FROM
  staging.players_career_pitching_stats s INNER JOIN players p ON
  s.player_id = p.player_id WHERE s.split_id = 1 ON DUPLICATE KEY UPDATE
  ...`, mirroring the batting insert at `migration_long.sql:48-69` (same
  `CASE WHEN team_id = 0 THEN 999 ELSE team_id END` handling).
- `backend/app/db/sql_scripts/api/get_player_career_pitching_mlb.sql` (new)
  and `get_player_career_pitching_milb.sql` (new): mirror
  `get_player_career_batting_mlb.sql` / `_milb.sql`'s per-year/team
  aggregation shape, `SUM`ing `w, l, s, g, gs, outs, k, bb, ha, er` (the
  columns the frontend table actually needs).
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
  new route in the existing `onMounted` `Promise.all`. `calcIp` (thirds
  notation from `outs`), `calcEra`, `calcWhip` helpers (all `null` on
  `outs === 0`), formatted via a new `formatEraWhip` variant — unlike
  AVG/OBP/SLG, ERA/WHIP conventionally keep their leading digit (`3.60`, not
  `.360`), so this is *not* the same `formatRate` used for batting rates.
  Same responsive/totals-row structure as the batting table, columns `Year,
  Team, W, L, ERA, G, GS, SV, IP, SO, WHIP`.
- `frontend/src/views/PlayerProfile.vue`: restructure the pitcher branch so
  `PitchRepertoire` renders directly below `PlayerDetails` in the left
  column (under the new career-stats table), instead of stacked with
  `PitcherPercentiles` in the right column — per the user-specified layout
  above. `PitcherPercentiles` remains alone in the right column.
- Manually verify against a real pitcher profile in the running app.

**Files involved:**
- `backend/app/db/staging.py` (modified)
- `backend/app/db/sql_scripts/schema.sql` (modified)
- `backend/app/db/sql_scripts/migration/migration_long.sql` (modified)
- `backend/app/db/sql_scripts/api/get_player_career_pitching_mlb.sql` (new)
- `backend/app/db/sql_scripts/api/get_player_career_pitching_milb.sql` (new)
- `backend/app/api/players.py` (modified)
- `backend/docs/openai.yaml` (modified)
- `frontend/src/components/PlayerDetails.vue` (modified)
- `frontend/src/views/PlayerProfile.vue` (modified)

**Verified (so far):** full pytest suite (same 11 pre-existing, unrelated
`test_players.py` failures, no new failures). Schema and migration verified
against a throwaway `mariadbd` instance loaded with the *real* `TEST.lg` save
data (not synthetic rows) — `schema.sql` applied cleanly, `players.mysql.sql`
/ `teams.mysql.sql` / `players_career_pitching_stats.mysql.sql` from the
2029 yearly heap loaded into a throwaway `staging` DB (405,532 raw rows),
`migration_long.sql`'s new `INSERT` ran without error and produced 369,405
rows in `ootp.players_career_pitching_stats`, spot-checked byte-for-byte
against the source dump (e.g. player 5's 2022 season). Both new SQL query
files (`get_player_career_pitching_mlb.sql` / `_milb.sql`) executed directly
against that data and returned correctly-shaped, plausible per-season lines.
The new `GET /api/players/<id>/career/pitching` route was exercised over
real HTTP (host `.venv` Flask pointed at the throwaway DB via the
`DB_HOST`/`DB_PORT` override pattern) — confirmed both the 200 list-of-seasons
case and the 404 not-found case. Frontend: `npm run build` inside the running
frontend container shows the same pre-existing `@/`-alias resolution errors
whether or not this ticket's frontend changes are applied (confirmed via
`git stash`), so nothing here introduces a new type error; no new errors
reference `PlayerDetails.vue` or `PlayerProfile.vue`'s changed lines. Not yet
verified in an actual browser against a real pitcher profile page.

**Live DB:** deliberately not applied to the user's real `ootp` database as
part of this work session — a plain `update-db` only ingests *new* heaps
(existing `processed_heaps` entries won't rerun), so backfilling historical
`players_career_pitching_stats` needs a full reprocess, which is slower and
more disruptive than the code change itself. Asked the user directly; they
chose to run that migration themselves on their own schedule rather than
having it done live in this session. Remaining before this ticket can close:
the user runs their own `init-db`/`update-db` (or equivalent reprocess) and
confirms the "Career Pitching Stats" + repertoire layout renders correctly
on a real pitcher profile page in the browser.
