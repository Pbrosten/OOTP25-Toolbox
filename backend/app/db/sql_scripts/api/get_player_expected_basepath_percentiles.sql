WITH target_player AS (
  SELECT r.rating_id, r.rating_date, r.league_id
  FROM players_rating r
  WHERE r.rating_id = ?
),

-- Ratings Comparison Group
ratings_filtered AS (
  SELECT b.*
  FROM players_basepath AS b
  JOIN players_rating AS r ON b.rating_id = r.rating_id
  JOIN players AS p ON r.player_id = p.player_id
  JOIN target_player AS t 
    ON r.rating_date = t.rating_date
    AND r.league_id = t.league_id
  WHERE p.position != 'P'
)

SELECT
  -- Rating based percentiles
  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM ratings_filtered
      WHERE speed < target_rate.speed AND speed IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM ratings_filtered WHERE speed IS NOT NULL
    )
   ) AS sprint_speed,

  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM ratings_filtered
      WHERE steal < target_rate.steal AND steal IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM ratings_filtered WHERE steal IS NOT NULL
    )
   ) AS steal_value,

  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM ratings_filtered
      WHERE baserunning < target_rate.baserunning AND baserunning IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM ratings_filtered WHERE baserunning IS NOT NULL
    )
   ) AS baserunning_value


FROM players_basepath AS target_rate 
WHERE target_rate.rating_id = ?;
