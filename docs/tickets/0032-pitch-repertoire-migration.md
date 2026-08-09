# 0032 — Ingest pitch repertoire: `migration_short.sql`

- **Tag:** feat
- **Status:** Open
- **Depends on:** [0031](0031-pitch-repertoire-schema.md)
- **Blocks:** [0033](0033-pitch-repertoire-report.md)

## 1. Problem

With `players_pitch_repertoire` in place (0031), nothing populates it yet —
`migration_short.sql` has no `INSERT` for it, and unlike 0025 there's no
staging re-enablement needed (`staging.players_pitching`, including its
24 per-pitch columns, is already loaded as of 0025).

## 2. Design choices

- **Twelve columns to twelve rows: `UNION ALL` vs. a single query.** MariaDB
  has no built-in unpivot/`CROSS JOIN` against a column list. **Chosen:** one
  `SELECT ... UNION ALL SELECT ...` per pitch type (12 `SELECT`s unioned),
  each selecting a literal `pitch_type` string and that type's
  `grade`/`talent_grade` columns, with the `WHERE ... > 0` filter applied
  per-branch — verbose but mechanical, matches this project's preference for
  explicit SQL over cleverness (e.g. `migration_short.sql`'s existing
  per-column `INSERT` lists), and every branch is identical modulo the
  column names being substituted, so it's easy to verify by inspection.
- **Filter predicate.** `grade > 0` per branch (see 0029/0031's Design
  choices for why this is the correct signal). Applied to `grade`, not
  `talent_grade` — confirmed by 0029's inspection that the two are zero on
  the same rows in practice, and `grade` (current) is the more natural
  column to gate on since `players_pitching`'s own `overall`/`talent` split
  treats `overall` as primary.
- **Scoping to pitchers.** Same `role IN (11, 12, 13)` filter already used
  for `players_pitching`/`players_pitching_talent` (see that block's
  comment in `migration_short.sql`) — non-pitchers have ~0 nonzero pitch
  columns anyway (confirmed by 0029's inspection), but the explicit filter
  keeps this insert's intent self-documenting and consistent with its
  sibling inserts rather than relying on the data happening to be empty.
- **Heap-date scoping.** Per [0009](0009-scope-ratings-detail-inserts-to-heap-date.md),
  `WHERE r.rating_date = '{{HEAP_DATE}}'` from day one, same as every other
  ratings-detail insert.

## 3. Approach

- `backend/app/db/sql_scripts/migration/migration_short.sql`: add one
  `INSERT IGNORE` block after the `players_pitching_talent` block:
  ```sql
  INSERT IGNORE INTO players_pitch_repertoire (rating_id, pitch_type, grade, talent_grade)
  SELECT r.rating_id, 'fastball', s.pitching_ratings_pitches_fastball, s.pitching_ratings_pitches_talent_fastball
  FROM players_rating AS r
  JOIN staging.players_pitching AS s ON r.player_id = s.player_id
  WHERE r.rating_date = '{{HEAP_DATE}}' AND s.role IN (11, 12, 13) AND s.pitching_ratings_pitches_fastball > 0
  UNION ALL
  SELECT r.rating_id, 'slider', s.pitching_ratings_pitches_slider, s.pitching_ratings_pitches_talent_slider
  FROM players_rating AS r
  JOIN staging.players_pitching AS s ON r.player_id = s.player_id
  WHERE r.rating_date = '{{HEAP_DATE}}' AND s.role IN (11, 12, 13) AND s.pitching_ratings_pitches_slider > 0
  -- ... one branch per remaining pitch type (curveball, screwball, forkball,
  -- changeup, sinker, splitter, knuckleball, cutter, circlechange,
  -- knucklecurve), same shape
  ;
  ```
- Verify against a real dump the same way 0025 did: run `update-db` against
  a save with a yearly heap already processed, confirm
  `players_pitch_repertoire` rows land (spot-check a known multi-pitch
  pitcher's row count and grades against the raw dump), and that
  `INSERT IGNORE` isn't silently no-opping.

**Files involved:**
- `backend/app/db/sql_scripts/migration/migration_short.sql` (modified)
