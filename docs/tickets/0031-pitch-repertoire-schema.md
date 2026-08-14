# 0031 — Pitch repertoire schema: `players_pitch_repertoire`

- **Tag:** feat
- **Status:** Closed
- **Depends on:** [0025](0025-pitcher-migration-ingestion.md)
- **Blocks:** [0032](0032-pitch-repertoire-migration.md)

## 1. Problem

[0029](0029-pitcher-pitch-repertoire.md) needs an `ootp`-schema home for
per-pitch-type grades before anything can be migrated or reported on. Today
the 24 per-pitch columns in `staging.players_pitching`
(`pitching_ratings_pitches_<type>` / `pitching_ratings_pitches_talent_<type>`)
have no destination table — 0024 deliberately excluded them from
`players_pitching`/`players_pitching_talent`.

## 2. Design choices

- **Storage shape: resolved by 0029.** Inspecting a real dump
  (`TEST.lg` save, 2029 yearly heap) confirmed the 24 per-pitch columns are
  `0` (not NULL) for pitch types a player doesn't throw and a real 20-80
  grade for ones they do — pitchers (`role IN (11,12,13)`) average 2-4
  nonzero pitches, non-pitchers average ~0. See 0029's Design choices for
  the full data. **Chosen: normalized** — one row per pitch actually
  thrown, not a 12-column-wide table with mostly-zero cells.
- **One table for current + talent grades, vs. mirroring the
  `players_pitching`/`players_pitching_talent` split.** The pitching schema
  splits current/talent into two tables because `players_pitching_talent`
  only exists for rows where the split is meaningful (it's still 1:1 on
  `rating_id`, both fixed-shape). Per-pitch data is different: current and
  talent grades are for the *same* `(rating_id, pitch_type)` pair, and
  splitting them would require the same `pitch_type` key twice across two
  tables for no benefit (no consumer reads one without the other).
  **Chosen:** a single `players_pitch_repertoire` table with both `grade`
  and `talent_grade` columns per row.
- **`pitch_type` representation: VARCHAR vs. an enum/lookup table.** The 12
  pitch types (`fastball`, `slider`, `curveball`, `screwball`, `forkball`,
  `changeup`, `sinker`, `splitter`, `knuckleball`, `cutter`,
  `circlechange`, `knucklecurve`) are fixed and never queried by anything
  other than exact match/display. **Chosen:** `VARCHAR(20)` matching the
  suffix of the source column name exactly (e.g. `circlechange`, not
  `circle_change`) — no separate lookup table, consistent with how this
  schema doesn't use lookup tables for other fixed small enumerations
  (e.g. `role`, `position` are raw SMALLINT/CHAR columns elsewhere).
- **Row-inclusion threshold.** Confirmed by 0029: `grade > 0` (equivalently
  `talent_grade > 0`, they're 0 on exactly the same rows per the
  inspection) is the correct predicate for "player throws this pitch." This
  is a migration-time (0032) decision, not a schema one — noted here so the
  two tickets agree.

## 3. Approach

- Add to `schema.sql` (alongside the existing pitching tables):
  ```sql
  CREATE TABLE players_pitch_repertoire (
    rating_id INT NOT NULL,
    pitch_type VARCHAR(20) NOT NULL,
    grade INT,
    talent_grade INT,
    PRIMARY KEY (rating_id, pitch_type),
    FOREIGN KEY (rating_id) REFERENCES players_rating(rating_id)
  ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
  ```
- Add a corresponding `DROP TABLE IF EXISTS players_pitch_repertoire;` line
  to the top of `schema.sql`, ordered before `players_rating`'s drop (same
  convention as the other pitching tables).

**Verified:** full pytest suite (same 11 pre-existing, unrelated
`test_players.py` failures noted in 0027; no new failures). No live
container stack available in this environment to run `init-db` end-to-end
against MariaDB — table/FK ordering was checked by inspection
(`players_rating` is created earlier in `schema.sql`, matching every other
per-rating table's FK) and matches the exact DDL from the ticket's Approach.

**Files involved:**
- `backend/app/db/sql_scripts/schema.sql` (modified)
