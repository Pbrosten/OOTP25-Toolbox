WITH target_player AS (
  SELECT r.rating_id, r.rating_date, r.league_id
  FROM players_rating r
  WHERE r.rating_id = ?
),

-- Expected Stats Comparison Group
expected_filtered AS (
  SELECT b.*
  FROM players_batting_expected AS b
  JOIN players_rating AS r ON b.rating_id = r.rating_id
  JOIN players AS p ON r.player_id = p.player_id
  JOIN target_player AS t 
    ON r.rating_date = t.rating_date
    AND r.league_id = t.league_id
  WHERE p.position != 'P'
),

-- Ratings Comparison Group
ratings_filtered AS (
  SELECT b.*
  FROM players_batting AS b
  JOIN players_rating AS r ON b.rating_id = r.rating_id
  JOIN players AS p ON r.player_id = p.player_id
  JOIN target_player AS t 
    ON r.rating_date = t.rating_date
    AND r.league_id = t.league_id
  WHERE p.position != 'P'
)

SELECT

  -- Projection based percentiles
  (
    SELECT COUNT(*) * 1.0
    FROM expected_filtered
    WHERE AVG < target_exp.AVG AND AVG IS NOT NULL
  ) / (SELECT COUNT(*) FROM expected_filtered WHERE AVG IS NOT NULL) AS xBA,

  (
    SELECT COUNT(*) * 1.0
    FROM expected_filtered
    WHERE SLG < target_exp.SLG AND SLG IS NOT NULL
  ) / (SELECT COUNT(*) FROM expected_filtered WHERE SLG IS NOT NULL) AS xSLG,

  (
    SELECT COUNT(*) * 1.0
    FROM expected_filtered
    WHERE wOBA < target_exp.wOBA AND wOBA IS NOT NULL
  ) / (SELECT COUNT(*) FROM expected_filtered WHERE wOBA IS NOT NULL) AS xWOBA,

  -- Rating based percentiles
  (
    SELECT COUNT(*) * 1.0
    FROM ratings_filtered
    WHERE babip < target_rate.gap AND gap IS NOT NULL
  ) / (SELECT COUNT(*) FROM ratings_filtered WHERE babip IS NOT NULL) AS xBABIP,

  (
    SELECT COUNT(*) * 1.0
    FROM ratings_filtered
    WHERE gap < target_rate.gap AND gap IS NOT NULL
  ) / (SELECT COUNT(*) FROM ratings_filtered WHERE gap IS NOT NULL) AS barrel_rate,

  (
    SELECT COUNT(*) * 1.0
    FROM ratings_filtered
    WHERE power < target_rate.gap AND power IS NOT NULL
  ) / (SELECT COUNT(*) FROM ratings_filtered WHERE gap IS NOT NULL) AS swing_speed,

  (
    SELECT COUNT(*) * 1.0
    FROM ratings_filtered
    WHERE eye < target_rate.gap AND eye IS NOT NULL
  ) / (SELECT COUNT(*) FROM ratings_filtered WHERE gap IS NOT NULL) AS chase_rate,

  (
    SELECT COUNT(*) * 1.0
    FROM ratings_filtered
    WHERE strikeouts < target_rate.gap AND strikeouts IS NOT NULL
  ) / (SELECT COUNT(*) FROM ratings_filtered WHERE gap IS NOT NULL) AS whiff_rate

FROM players_batting_expected AS target_exp
JOIN players_batting AS target_rate ON target_exp.rating_id = target_rate.rating_id
WHERE target_exp.rating_id = ?;
