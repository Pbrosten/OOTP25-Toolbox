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
   ) AS whiff_rate,

  -- Potential percentiles (ticket 0086): the target's *_talent (ceiling)
  -- value/grade, ranked against the exact same current-population CTEs
  -- above -- "if this player reached their ceiling today, where would
  -- they rank against today's league". LEFT JOINed below, so a missing
  -- talent projection (e.g. process_player()'s potential-run failed for
  -- this rating) degrades to NULL rather than dropping the whole row.
  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM expected_filtered
      WHERE AVG < target_exp_talent.AVG AND AVG IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM expected_filtered WHERE AVG IS NOT NULL
    )
   ) AS xba_percentile_potential,

  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM expected_filtered
      WHERE SLG < target_exp_talent.SLG AND SLG IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM expected_filtered WHERE SLG IS NOT NULL
    )
   ) AS xslg_percentile_potential,

  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM expected_filtered
      WHERE wOBA < target_exp_talent.wOBA AND wOBA IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM expected_filtered WHERE wOBA IS NOT NULL
    )
   ) AS xwoba_percentile_potential,

  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM ratings_filtered
      WHERE babip < target_rate_talent.babip AND babip IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM ratings_filtered WHERE babip IS NOT NULL
    )
   ) AS xbabip_percentile_potential,

  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM ratings_filtered
      WHERE gap < target_rate_talent.gap AND gap IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM ratings_filtered WHERE gap IS NOT NULL
    )
   ) AS barrel_rate_potential,

  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM ratings_filtered
      WHERE power < target_rate_talent.power AND power IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM ratings_filtered WHERE power IS NOT NULL
    )
   ) AS swing_speed_potential,

  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM ratings_filtered
      WHERE eye < target_rate_talent.eye AND eye IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM ratings_filtered WHERE eye IS NOT NULL
    )
   ) AS chase_rate_potential,

  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM ratings_filtered
      WHERE strikeouts < target_rate_talent.strikeouts AND strikeouts IS NOT NULL
    ) * 100 /
    (
      SELECT COUNT(*) FROM ratings_filtered WHERE strikeouts IS NOT NULL
    )
   ) AS whiff_rate_potential,

  -- Raw values alongside each percentile above -- only for genuine
  -- projected statistics (players_batting_expected), not the raw game
  -- ratings above (babip/gap/power/eye/strikeouts) that borrow outcome-stat
  -- names in the frontend (see BatterPercentiles.vue's statLabelMap):
  -- showing their raw 20-80 grade next to that name would misrepresent it
  -- as a real rate stat -- same reasoning as the pitching percentiles
  -- query.
  target_exp.AVG AS xba_value,
  target_exp.SLG AS xslg_value,
  target_exp.wOBA AS xwoba_value,

  target_exp_talent.AVG AS xba_value_potential,
  target_exp_talent.SLG AS xslg_value_potential,
  target_exp_talent.wOBA AS xwoba_value_potential

FROM players_batting_expected AS target_exp
JOIN players_batting AS target_rate ON target_exp.rating_id = target_rate.rating_id
LEFT JOIN players_batting_expected_talent AS target_exp_talent ON target_exp.rating_id = target_exp_talent.rating_id
LEFT JOIN players_batting_talent AS target_rate_talent ON target_exp.rating_id = target_rate_talent.rating_id
WHERE target_exp.rating_id = %(rating_id)s;
