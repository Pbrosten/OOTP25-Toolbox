WITH target_player AS (
  SELECT r.rating_id, r.rating_date, r.league_id
  FROM players_rating r
  WHERE r.rating_id = %(rating_id)s
),

-- Expected Stats Comparison Group
expected_filtered AS (
  SELECT pe.*
  FROM players_pitching_expected AS pe
  JOIN players_rating AS r ON pe.rating_id = r.rating_id
  JOIN players AS p ON r.player_id = p.player_id
  JOIN target_player AS t ON r.rating_date = t.rating_date
  WHERE
    p.position = 'P'
    AND p.team_id != 999
    AND r.league_id = t.league_id
    AND (
      (t.league_id = 203 AND p.age >= 22)
      OR (t.league_id <> 203)
    )
),

-- Ratings Comparison Group
ratings_filtered AS (
  SELECT pp.*
  FROM players_pitching AS pp
  JOIN players_rating AS r ON pp.rating_id = r.rating_id
  JOIN players AS p ON r.player_id = p.player_id
  JOIN target_player AS t ON r.rating_date = t.rating_date
  WHERE
    p.position = 'P'
    AND p.team_id != 999
    AND r.league_id = t.league_id
    AND (
      (t.league_id = 203 AND p.age >= 22)
      OR (t.league_id <> 203)
    )
),

-- Value Comparison Group
value_filtered AS (
  SELECT pv.*
  FROM players_pitching_run_value AS pv
  JOIN players_rating AS r ON pv.rating_id = r.rating_id
  JOIN players AS p ON r.player_id = p.player_id
  JOIN target_player AS t ON r.rating_date = t.rating_date
  WHERE
    p.position = 'P'
    AND p.team_id != 999
    AND r.league_id = t.league_id
    AND (
      (t.league_id = 203 AND p.age >= 22)
      OR (t.league_id <> 203)
    )
),

-- Pitch-category grade comparison group (ticket 0034): one row per
-- rating_id, average players_pitch_repertoire.grade within each of the
-- three Fastball/Breaking/Offspeed categories (see 0034's Design choices
-- for the pitch-type -> category mapping). NULL for a category the
-- pitcher throws nothing in, same NULL-exclusion convention as every
-- other percentile in this file.
pitch_category_filtered AS (
  SELECT
    pr.rating_id,
    AVG(CASE WHEN pr.pitch_type IN ('fastball', 'sinker', 'cutter') THEN pr.grade END) AS fastball_grade,
    AVG(CASE WHEN pr.pitch_type IN ('slider', 'curveball', 'knucklecurve') THEN pr.grade END) AS breaking_grade,
    AVG(CASE WHEN pr.pitch_type IN ('changeup', 'splitter', 'forkball', 'circlechange', 'knuckleball', 'screwball') THEN pr.grade END) AS offspeed_grade
  FROM players_pitch_repertoire AS pr
  JOIN players_rating AS r ON pr.rating_id = r.rating_id
  JOIN players AS p ON r.player_id = p.player_id
  JOIN target_player AS t ON r.rating_date = t.rating_date
  WHERE
    p.position = 'P'
    AND p.team_id != 999
    AND r.league_id = t.league_id
    AND (
      (t.league_id = 203 AND p.age >= 22)
      OR (t.league_id <> 203)
    )
  GROUP BY pr.rating_id
),

-- Target player's own category grades, computed unfiltered (same pattern
-- as target_exp/target_rate/target_val being read straight off the base
-- tables below, not the cohort-filtered CTEs).
target_cat AS (
  SELECT
    pr.rating_id,
    AVG(CASE WHEN pr.pitch_type IN ('fastball', 'sinker', 'cutter') THEN pr.grade END) AS fastball_grade,
    AVG(CASE WHEN pr.pitch_type IN ('slider', 'curveball', 'knucklecurve') THEN pr.grade END) AS breaking_grade,
    AVG(CASE WHEN pr.pitch_type IN ('changeup', 'splitter', 'forkball', 'circlechange', 'knuckleball', 'screwball') THEN pr.grade END) AS offspeed_grade
  FROM players_pitch_repertoire AS pr
  WHERE pr.rating_id = %(rating_id)s
  GROUP BY pr.rating_id
)

SELECT

  -- Value percentiles (higher runs/WAR is better)
  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM value_filtered
      WHERE pitching_runs < target_val.pitching_runs AND pitching_runs IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM value_filtered WHERE pitching_runs IS NOT NULL
    )
   ) AS pitching_runs_percentile,

  -- Fastball/Breaking/Offspeed grade percentiles (ticket 0034) -- combined
  -- quality of all pitch types in each category, percentiled directly
  -- against the rest of pitchers (not tied to pitching_runs/run-value at
  -- all). Higher grade is better, same direction as the rating percentiles
  -- below. Explicit CASE guard: without it, a NULL target_cat.*_grade
  -- (pitcher throws nothing in that category) silently computes to a
  -- misleading 0 rather than NULL -- COUNT(*) against a `< NULL` WHERE
  -- clause returns a real 0, it doesn't propagate NULL the way a scalar
  -- comparison would.
  CASE WHEN target_cat.fastball_grade IS NOT NULL THEN ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM pitch_category_filtered
      WHERE fastball_grade < target_cat.fastball_grade AND fastball_grade IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM pitch_category_filtered WHERE fastball_grade IS NOT NULL
    )
   ) END AS fastball_grade_percentile,

  CASE WHEN target_cat.breaking_grade IS NOT NULL THEN ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM pitch_category_filtered
      WHERE breaking_grade < target_cat.breaking_grade AND breaking_grade IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM pitch_category_filtered WHERE breaking_grade IS NOT NULL
    )
   ) END AS breaking_grade_percentile,

  CASE WHEN target_cat.offspeed_grade IS NOT NULL THEN ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM pitch_category_filtered
      WHERE offspeed_grade < target_cat.offspeed_grade AND offspeed_grade IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM pitch_category_filtered WHERE offspeed_grade IS NOT NULL
    )
   ) END AS offspeed_grade_percentile,

  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM value_filtered
      WHERE baserunning_runs < target_val.baserunning_runs AND baserunning_runs IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM value_filtered WHERE baserunning_runs IS NOT NULL
    )
   ) AS baserunning_runs_percentile,

  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM value_filtered
      WHERE total_runs < target_val.total_runs AND total_runs IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM value_filtered WHERE total_runs IS NOT NULL
    )
   ) AS total_runs_percentile,

  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM value_filtered
      WHERE WAR < target_val.WAR AND WAR IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM value_filtered WHERE WAR IS NOT NULL
    )
   ) AS war_percentile,

  -- Projection based percentiles (lower ERA/BA/wOBA-against is better -- comparisons inverted)
  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM expected_filtered
      WHERE ERA > target_exp.ERA AND ERA IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM expected_filtered WHERE ERA IS NOT NULL
    )
   ) AS era_percentile,

  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM expected_filtered
      WHERE BA > target_exp.BA AND BA IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM expected_filtered WHERE BA IS NOT NULL
    )
   ) AS xba_percentile,

  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM expected_filtered
      WHERE wOBA > target_exp.wOBA AND wOBA IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM expected_filtered WHERE wOBA IS NOT NULL
    )
   ) AS xwoba_percentile,

  -- Rating based percentiles (higher rating is better for all of these)
  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM ratings_filtered
      WHERE stuff < target_rate.stuff AND stuff IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM ratings_filtered WHERE stuff IS NOT NULL
    )
   ) AS stuff_percentile,

  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM ratings_filtered
      WHERE control < target_rate.control AND control IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM ratings_filtered WHERE control IS NOT NULL
    )
   ) AS control_percentile,

  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM ratings_filtered
      WHERE pbabip < target_rate.pbabip AND pbabip IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM ratings_filtered WHERE pbabip IS NOT NULL
    )
   ) AS pbabip_percentile,

  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM ratings_filtered
      WHERE hra < target_rate.hra AND hra IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM ratings_filtered WHERE hra IS NOT NULL
    )
   ) AS hra_percentile,

  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM ratings_filtered
      WHERE stamina < target_rate.stamina AND stamina IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM ratings_filtered WHERE stamina IS NOT NULL
    )
   ) AS stamina_percentile,

  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM ratings_filtered
      WHERE hold < target_rate.hold AND hold IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM ratings_filtered WHERE hold IS NOT NULL
    )
   ) AS hold_percentile,

  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM ratings_filtered
      WHERE velocity < target_rate.velocity AND velocity IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM ratings_filtered WHERE velocity IS NOT NULL
    )
   ) AS velocity_percentile,

  -- Raw values alongside each percentile above, for display next to the
  -- percentile bar (Savant-style raw-value column) -- only for genuine
  -- projected statistics (PitcherProjection output), not raw game ratings
  -- (stuff/control/pbabip/hra/velocity, pitch-category grades): those
  -- borrow outcome-stat names in the frontend (see PitcherPercentiles.vue's
  -- statLabelMap) but showing their raw 20-80 grade next to that name would
  -- misrepresent it as a real rate stat. Named <stat>_value so the
  -- frontend can derive the lookup key from each *_percentile key
  -- mechanically.
  target_val.pitching_runs AS pitching_runs_value,
  target_exp.ERA AS era_value,
  target_exp.BA AS xba_value,
  target_exp.wOBA AS xwoba_value

FROM players_pitching_expected AS target_exp
JOIN players_pitching AS target_rate ON target_exp.rating_id = target_rate.rating_id
JOIN players_pitching_run_value AS target_val ON target_exp.rating_id = target_val.rating_id
LEFT JOIN target_cat ON target_exp.rating_id = target_cat.rating_id
WHERE target_exp.rating_id = %(rating_id)s;
