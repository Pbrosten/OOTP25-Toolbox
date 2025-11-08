WITH target_player AS (
  SELECT r.rating_id, r.rating_date, r.league_id
  FROM players_rating r
  WHERE r.rating_id = %(rating_id)s
),

-- Expected Stats Comparison Group
expected_filtered AS (
  SELECT rv.*
  FROM players_run_value AS rv
  JOIN players_rating AS r ON rv.rating_id = r.rating_id
  JOIN players AS p ON r.player_id = p.player_id
  JOIN target_player AS t 
    ON r.rating_date = t.rating_date
    AND (
      (%(is_milb)s = 1 AND r.league_id = t.league_id)
      OR (%(is_milb)s = 0 AND r.league_id = 203)
    )
  WHERE p.position != 'P'
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

   ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM expected_filtered
      WHERE fielding_runs < target_exp.fielding_runs AND fielding_runs IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM expected_filtered WHERE fielding_runs IS NOT NULL
    )
   ) AS fielding_runs_percentile,

   ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM expected_filtered
      WHERE total_runs < target_exp.total_runs AND total_runs IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM expected_filtered WHERE total_runs IS NOT NULL
    )
   ) AS total_runs_percentile


FROM players_run_value AS target_exp
WHERE target_exp.rating_id = %(rating_id)s;
