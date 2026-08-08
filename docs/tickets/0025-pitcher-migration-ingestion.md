# 0025 — Ingest pitcher ratings: re-enable staging load + `migration_short.sql`

- **Tag:** feat
- **Status:** Closed
- **Depends on:** [0024](0024-pitcher-schema-ratings-tables.md)
- **Blocks:** [0026](0026-pitcher-projection-methodology.md)

## 1. Problem

Even with `ootp.players_pitching`/`players_pitching_talent` in place (0024),
nothing populates them: `players_pitching` isn't loaded into `staging` at all
([0014](0014-drop-unused-pitching-ingestion.md) removed it, since nothing
downstream read it), and `migration_short.sql` has no `INSERT` statements for
it.

## 2. Design choices

- **Re-adding to `DUMP_INCLUSION_LIST`.** This is 0015's Approach step ("Re-add
  `players_pitching` if 0014 shipped first") — 0014 did ship, so this ticket
  reverses that specific line. No alternative considered; this is the whole
  point of 0015 superseding 0014.
- **Join shape.** Same pattern as the existing batting inserts in
  `migration_short.sql`: `INNER JOIN staging.players_pitching AS s ON
  r.player_id = s.player_id`. An `INNER JOIN` (not `LEFT JOIN`) is correct
  here, not incidental — confirmed by inspecting a real heap that
  `staging.players_pitching` only contains rows for pitching-capable players
  (119/218 players in the sample heap), so the join itself does the "only
  pitchers get a row" filtering, matching how the batting join implicitly
  excludes pure pitchers today.
- **Scope ratings-detail inserts to the heap date from the start.** Per
  [0009](0009-scope-ratings-detail-inserts-to-heap-date.md), every new
  `INSERT ... FROM players_rating AS r JOIN staging....` must carry
  `WHERE r.rating_date = '{{HEAP_DATE}}'` from day one — not deferred to a
  follow-up fix.

## 3. Approach

- `backend/app/db/staging.py`: add `"players_pitching"` back to
  `DUMP_INCLUSION_LIST` (`backend/app/db/staging.py:9-15`).
- `backend/app/db/sql_scripts/migration/migration_short.sql`: add two
  `INSERT IGNORE` blocks after the existing `players_batting_talent` block,
  following the established pattern exactly:
  ```sql
  INSERT IGNORE INTO players_pitching (
      rating_id, stuff, movement, hra, pbabip, control, balk, hp, wild_pitch,
      velocity, arm_slot, stamina, ground_fly, hold
  )
  SELECT
      r.rating_id,
      s.pitching_ratings_overall_stuff,
      s.pitching_ratings_overall_movement,
      s.pitching_ratings_overall_hra,
      s.pitching_ratings_overall_pbabip,
      s.pitching_ratings_overall_control,
      s.pitching_ratings_overall_balk,
      s.pitching_ratings_overall_hp,
      s.pitching_ratings_overall_wild_pitch,
      s.pitching_ratings_misc_velocity,
      s.pitching_ratings_misc_arm_slot,
      s.pitching_ratings_misc_stamina,
      s.pitching_ratings_misc_ground_fly,
      s.pitching_ratings_misc_hold
  FROM players_rating AS r
  JOIN staging.players_pitching AS s ON r.player_id = s.player_id
  WHERE r.rating_date = '{{HEAP_DATE}}';

  INSERT IGNORE INTO players_pitching_talent (
      rating_id, stuff, movement, hra, pbabip, control, balk, hp, wild_pitch
  )
  SELECT
      r.rating_id,
      s.pitching_ratings_talent_stuff,
      s.pitching_ratings_talent_movement,
      s.pitching_ratings_talent_hra,
      s.pitching_ratings_talent_pbabip,
      s.pitching_ratings_talent_control,
      s.pitching_ratings_talent_balk,
      s.pitching_ratings_talent_hp,
      s.pitching_ratings_talent_wild_pitch
  FROM players_rating AS r
  JOIN staging.players_pitching AS s ON r.player_id = s.player_id
  WHERE r.rating_date = '{{HEAP_DATE}}';
  ```
- `migration_long.sql`: confirmed no changes needed — it only seeds
  `players`/`teams` and updates ages, doesn't touch per-heap ratings
  snapshots.
- Verify against a real dump (`update-db` against a save with a yearly heap
  processed first, per this repo's existing "at least one yearly dump must be
  present" constraint) that `players_pitching` rows land correctly and
  `INSERT IGNORE` doesn't silently no-op due to a FK/date mismatch — this
  exact class of bug is what 0009 fixed on the batting side.

**Files involved:**
- `backend/app/db/staging.py` (modified)
- `backend/app/db/sql_scripts/migration/migration_short.sql` (modified)
