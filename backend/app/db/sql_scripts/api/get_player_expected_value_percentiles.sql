WITH target_player AS (
  SELECT r.rating_id, r.rating_date, r.league_id, p.position
  FROM players_rating r
  JOIN players p ON p.player_id = r.player_id
  WHERE r.rating_id = %(rating_id)s
),

-- Expected Stats Comparison Group. DH is excluded alongside pitchers -- DH
-- has no real fielding value, so pooling it into the fielding_runs
-- comparison pool is meaningless (ticket 0060).
expected_filtered AS (
  SELECT rv.*
  FROM players_run_value AS rv
  JOIN players_rating AS r ON rv.rating_id = r.rating_id
  JOIN players AS p ON r.player_id = p.player_id
  JOIN target_player AS t ON r.rating_date = t.rating_date
  WHERE
    p.position NOT IN ('P', 'DH')
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
      WHERE batting_runs < target_exp.batting_runs AND batting_runs IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM expected_filtered WHERE batting_runs IS NOT NULL
    )
   ) AS batting_runs_percentile,

   ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM expected_filtered
      WHERE basepath_runs < target_exp.basepath_runs AND basepath_runs IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM expected_filtered WHERE basepath_runs IS NOT NULL
    )
   ) AS basepath_runs_percentile,

   CASE WHEN target_player.position = 'DH' THEN NULL ELSE ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM expected_filtered
      WHERE fielding_runs < target_exp.fielding_runs AND fielding_runs IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM expected_filtered WHERE fielding_runs IS NOT NULL
    )
   ) END AS fielding_runs_percentile,

   ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM expected_filtered
      WHERE total_runs < target_exp.total_runs AND total_runs IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM expected_filtered WHERE total_runs IS NOT NULL
    )
   ) AS total_runs_percentile,

  -- Raw values alongside each percentile above (all four are genuine
  -- projected run values, not raw game ratings, so all get one -- unlike
  -- the batting/fielding percentile queries where some fields borrow
  -- outcome-stat names for raw scouting grades).
  target_exp.batting_runs AS batting_runs_value,
  target_exp.basepath_runs AS basepath_runs_value,
  CASE WHEN target_player.position = 'DH' THEN NULL ELSE target_exp.fielding_runs END AS fielding_runs_value,
  target_exp.total_runs AS total_runs_value

FROM players_run_value AS target_exp
JOIN target_player ON target_player.rating_id = target_exp.rating_id
WHERE target_exp.rating_id = %(rating_id)s;
