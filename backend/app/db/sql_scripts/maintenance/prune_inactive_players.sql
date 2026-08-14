-- One-time cleanup for ticket 0046: removes players who are both retired
-- and inactive since before 2024, plus every row that FK-depends on them
-- (schema.sql declares no ON DELETE CASCADE anywhere, so this has to walk
-- the dependency chain explicitly, leaves first). Mirrors the same
-- retired/2024 predicate migration_long.sql now applies at ingestion --
-- see that file's comment above the `players` INSERT for the reasoning
-- (retired=0 players are always kept, regardless of recent stat history).
--
-- Run this against a throwaway copy of the database first and confirm the
-- row counts look right before ever pointing it at the real `ootp`
-- database -- it is destructive and has no undo.
USE ootp;

DROP TEMPORARY TABLE IF EXISTS prune_player_ids;
CREATE TEMPORARY TABLE prune_player_ids AS
SELECT p.player_id
FROM players p
WHERE p.retired = 1
  AND p.player_id NOT IN (
        SELECT player_id FROM players_career_batting_stats WHERE year >= 2024
        UNION
        SELECT player_id FROM players_career_pitching_stats WHERE year >= 2024
      );

DROP TEMPORARY TABLE IF EXISTS prune_rating_ids;
CREATE TEMPORARY TABLE prune_rating_ids AS
SELECT rating_id FROM players_rating
WHERE player_id IN (SELECT player_id FROM prune_player_ids);

-- Batting chain
DELETE FROM players_batting_expected WHERE rating_id IN (SELECT rating_id FROM prune_rating_ids);
DELETE FROM players_batting_talent WHERE rating_id IN (SELECT rating_id FROM prune_rating_ids);
DELETE FROM players_batting WHERE rating_id IN (SELECT rating_id FROM prune_rating_ids);

-- Pitching chain
DELETE FROM players_pitching_expected WHERE rating_id IN (SELECT rating_id FROM prune_rating_ids);
DELETE FROM players_pitching_talent WHERE rating_id IN (SELECT rating_id FROM prune_rating_ids);
DELETE FROM players_pitching WHERE rating_id IN (SELECT rating_id FROM prune_rating_ids);

-- Pitch repertoire
DELETE FROM players_pitch_repertoire WHERE rating_id IN (SELECT rating_id FROM prune_rating_ids);

-- Basepath chain
DELETE FROM players_basepath_expected WHERE rating_id IN (SELECT rating_id FROM prune_rating_ids);
DELETE FROM players_basepath WHERE rating_id IN (SELECT rating_id FROM prune_rating_ids);

-- Fielding chain
DELETE FROM players_fielding_expected WHERE rating_id IN (SELECT rating_id FROM prune_rating_ids);
DELETE FROM players_fielding_position_talent WHERE rating_id IN (SELECT rating_id FROM prune_rating_ids);
DELETE FROM players_fielding_position WHERE rating_id IN (SELECT rating_id FROM prune_rating_ids);
DELETE FROM players_fielding WHERE rating_id IN (SELECT rating_id FROM prune_rating_ids);

-- Run value
DELETE FROM players_run_value WHERE rating_id IN (SELECT rating_id FROM prune_rating_ids);
DELETE FROM players_pitching_run_value WHERE rating_id IN (SELECT rating_id FROM prune_rating_ids);

-- Rating snapshots and career stats
DELETE FROM players_rating WHERE player_id IN (SELECT player_id FROM prune_player_ids);
DELETE FROM players_career_batting_stats WHERE player_id IN (SELECT player_id FROM prune_player_ids);
DELETE FROM players_career_pitching_stats WHERE player_id IN (SELECT player_id FROM prune_player_ids);

-- players_similarity has no declared FK/engine (looks vestigial -- see
-- ticket 0046's Design choices) but is still cleaned up for consistency,
-- matched on either side of the pair.
DELETE FROM players_similarity
WHERE player_main IN (SELECT player_id FROM prune_player_ids)
   OR player_comp IN (SELECT player_id FROM prune_player_ids);

DELETE FROM players WHERE player_id IN (SELECT player_id FROM prune_player_ids);

DROP TEMPORARY TABLE IF EXISTS prune_rating_ids;
DROP TEMPORARY TABLE IF EXISTS prune_player_ids;
