WITH target_player AS (
  SELECT r.rating_id, r.rating_date, r.league_id
  FROM players_rating r
  WHERE r.rating_id = %(rating_id)s
),

-- Expected Stats Comparison Group
expected_filtered AS (
  SELECT b.*
  FROM players_batting_expected AS b
  JOIN players_rating AS r ON b.rating_id = r.rating_id
  JOIN players AS p ON r.player_id = p.player_id
  JOIN target_player AS t ON r.rating_date = t.rating_date
  WHERE 
    p.position != 'P'
    AND p.team_id != 999
    AND r.league_id = t.league_id
    AND (
      (t.league_id = 203 AND p.age >= 22)
      OR (t.league_id <> 203)
    )
),

-- Ratings Comparison Group
ratings_filtered AS (
  SELECT b.*
  FROM players_batting AS b
  JOIN players_rating AS r ON b.rating_id = r.rating_id
  JOIN players AS p ON r.player_id = p.player_id
  JOIN target_player AS t ON r.rating_date = t.rating_date
  WHERE 
    p.position != 'P'
    AND p.team_id != 999
    AND r.league_id = t.league_id
    AND (
      (t.league_id = 203 AND p.age >= 22)
      OR (t.league_id <> 203)
    )
)

SELECT

  -- Projection based percentiles
  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM expected_filtered
      WHERE AVG < target_exp.AVG AND AVG IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM expected_filtered WHERE AVG IS NOT NULL
    )
   ) AS xba_percentile,

  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM expected_filtered
      WHERE SLG < target_exp.SLG AND SLG IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM expected_filtered WHERE SLG IS NOT NULL
    )
   ) AS xslg_percentile,

  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM expected_filtered
      WHERE wOBA < target_exp.wOBA AND wOBA IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM expected_filtered WHERE wOBA IS NOT NULL
    )
   ) AS xwoba_percentile,

  -- Rating based percentiles
  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM ratings_filtered
      WHERE babip < target_rate.babip AND babip IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM ratings_filtered WHERE babip IS NOT NULL
    )
   ) AS xbabip_percentile,

  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM ratings_filtered
      WHERE gap < target_rate.gap AND gap IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM ratings_filtered WHERE gap IS NOT NULL
    )
   ) AS barrel_rate,

  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM ratings_filtered
      WHERE power < target_rate.power AND power IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM ratings_filtered WHERE power IS NOT NULL
    )
   ) AS swing_speed,

  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM ratings_filtered
      WHERE eye < target_rate.eye AND eye IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM ratings_filtered WHERE eye IS NOT NULL
    )
   ) AS chase_rate,

  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM ratings_filtered
      WHERE strikeouts < target_rate.strikeouts AND strikeouts IS NOT NULL
    ) * 100 / 
    (
      SELECT COUNT(*) FROM ratings_filtered WHERE strikeouts IS NOT NULL
    )
   ) AS whiff_rate

FROM players_batting_expected AS target_exp
JOIN players_batting AS target_rate ON target_exp.rating_id = target_rate.rating_id
WHERE target_exp.rating_id = %(rating_id)s;