# 0024 — Pitcher ratings schema: `players_pitching` / `players_pitching_talent`

- **Tag:** feat
- **Status:** Closed
- **Depends on:** —
- **Blocks:** [0025](0025-pitcher-migration-ingestion.md)

## 1. Problem

[0015](0015-pitcher-projection-epic.md) needs an `ootp`-schema home for pitcher
ratings before anything can be migrated or projected. Today there is no
`players_pitching` table in `schema.sql` — only the staging copy of OOTP's raw
export (when ingested at all; currently excluded per
[0014](0014-drop-unused-pitching-ingestion.md)).

This ticket resolves 0015's first "Outstanding" question far enough to unblock
schema work, by inspecting a real dump export
(`staging.players_pitching`, `TEST.lg` save, 2029 yearly heap) rather than
guessing at column names.

## 2. Design choices

- **What does `staging.players_pitching` actually contain?** 67 columns:
  `player_id`, `team_id`, `league_id`, `position`, `role`, then four rating
  "families" over the same 8 pitch-quality attributes (`stuff`, `movement`,
  `hra`, `pbabip`, `control`, `balk`, `hp`, `wild_pitch`) — `overall`, `vsr`
  (vs. RHB), `vsl` (vs. LHB), `talent` — plus per-pitch-type grades (12 pitch
  types × current/talent = 24 columns, e.g. `pitching_ratings_pitches_fastball`,
  `pitching_ratings_pitches_talent_fastball`) and 5 `misc` columns
  (`velocity`, `arm_slot`, `stamina`, `ground_fly`, `hold`). Row count in the
  sample heap (119 rows) confirms it's scoped to pitching-capable players only,
  same shape as `staging.players_batting` (80 rows) is scoped to batters —
  an `INNER JOIN` in migration will naturally exclude non-pitchers, no filter
  needed.
- **Full 1:1 mirror vs. trimmed set, mirroring the batting schema's shape?**
  `players_batting` only stores `overall` ratings (8 cols) plus 2 misc
  (`bunt`, `bunt_for_hit`); `vsl`/`vsr` splits don't exist on the batting side
  at all, and `talent` ratings live in a separate `players_batting_talent`.
  Options: (a) mirror all 67 raw columns into one wide table, (b) mirror the
  batting pattern — `overall` + `misc` ratings in `players_pitching`,
  `talent` ratings in a parallel `players_pitching_talent`, defer `vsl`/`vsr`
  splits and the 24 per-pitch-type grade columns since no consumer needs them
  yet. **Chosen: (b)** — consistent with the existing schema's shape and
  0015's Approach ("mirroring the batting side"); adding unused columns now
  is exactly the kind of speculative surface this project's conventions
  avoid.
- **`players_pitching_expected` columns.** Left undefined by this ticket —
  its shape depends entirely on [0026](0026-pitcher-projection-methodology.md)'s
  chosen output stats (ERA? FIP? counting stats like IP/K/BB/HR?). Creating
  it here with guessed columns would just require an immediate follow-up
  migration once 0026 lands.
- **Run-value / WAR table: extend `players_run_value` or add a parallel
  table?** `players_run_value` is keyed 1:1 on `rating_id`
  (`players_rating`), which is shared per player per `rating_date` regardless
  of player type — a two-way player has exactly one `rating_id` per heap.
  Extending the existing table with a `pitching_runs` column would force a
  decision about how `total_runs`/`WAR` combine batting and pitching value
  for two-way players; a parallel `players_pitching_run_value` table keeps
  pitching WAR independent (matching how the frontend's stubbed
  `PitcherPercentiles` is a separate component from batter percentiles) at
  the cost of the API needing to sum both tables for two-way players.
  **Outstanding — not decided here, left for 0026** since it's a projection
  question (does the methodology even want to net batting/pitching value?),
  not a schema-mechanics one.

## 3. Approach

- Add to `schema.sql` (alongside the existing `DROP TABLE IF EXISTS` block and
  the batting/fielding/basepath tables):
  ```sql
  CREATE TABLE players_pitching (
    rating_id INT PRIMARY KEY,
    stuff INT,
    movement INT,
    hra INT,
    pbabip INT,
    control INT,
    balk INT,
    hp INT,
    wild_pitch INT,
    velocity INT,
    arm_slot INT,
    stamina INT,
    ground_fly INT,
    hold INT,
    FOREIGN KEY (rating_id) REFERENCES players_rating(rating_id)
  ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

  CREATE TABLE players_pitching_talent (
    rating_id INT PRIMARY KEY,
    stuff INT,
    movement INT,
    hra INT,
    pbabip INT,
    control INT,
    balk INT,
    hp INT,
    wild_pitch INT,
    FOREIGN KEY (rating_id) REFERENCES players_rating(rating_id)
  ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
  ```
- Add corresponding `DROP TABLE IF EXISTS players_pitching_talent;` /
  `DROP TABLE IF EXISTS players_pitching;` lines to the top of `schema.sql`,
  ordered before `players_rating`'s drop (same convention as the batting
  tables).
- Do **not** add `players_pitching_expected` or a pitching run-value table in
  this ticket — that's 0025/0026's job once the migration and methodology are
  settled enough to know the column shapes.

**Files involved:**
- `backend/app/db/sql_scripts/schema.sql` (modified)
