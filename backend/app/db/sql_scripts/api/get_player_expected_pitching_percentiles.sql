WITH target_player AS (
  SELECT r.rating_id, r.rating_date, r.league_id,
    CASE WHEN pp.role = 11 THEN 'SP' ELSE 'RP' END AS role_group
  FROM players_rating r
  JOIN players_pitching pp ON pp.rating_id = r.rating_id
  WHERE r.rating_id = %(rating_id)s
),

-- Expected Stats Comparison Group
expected_filtered AS (
  SELECT pe.*
  FROM players_pitching_expected AS pe
  JOIN players_rating AS r ON pe.rating_id = r.rating_id
  JOIN players AS p ON r.player_id = p.player_id
  JOIN players_pitching AS pp ON pe.rating_id = pp.rating_id
  JOIN target_player AS t ON r.rating_date = t.rating_date
  WHERE
    p.position = 'P'
    AND p.team_id != 999
    AND r.league_id = t.league_id
    AND (CASE WHEN pp.role = 11 THEN 'SP' ELSE 'RP' END) = t.role_group
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
    AND (CASE WHEN pp.role = 11 THEN 'SP' ELSE 'RP' END) = t.role_group
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
  JOIN players_pitching AS pp ON pv.rating_id = pp.rating_id
  JOIN target_player AS t ON r.rating_date = t.rating_date
  WHERE
    p.position = 'P'
    AND p.team_id != 999
    AND r.league_id = t.league_id
    AND (CASE WHEN pp.role = 11 THEN 'SP' ELSE 'RP' END) = t.role_group
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
  JOIN players_pitching AS pp ON pr.rating_id = pp.rating_id
  JOIN target_player AS t ON r.rating_date = t.rating_date
  WHERE
    p.position = 'P'
    AND p.team_id != 999
    AND r.league_id = t.league_id
    AND (CASE WHEN pp.role = 11 THEN 'SP' ELSE 'RP' END) = t.role_group
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
),

-- Potential (ticket 0086): same target category averages, but off each
-- pitch's talent_grade (already ingested onto players_pitch_repertoire
-- itself -- no new table needed here unlike the other potential columns
-- in this file).
target_cat_talent AS (
  SELECT
    pr.rating_id,
    AVG(CASE WHEN pr.pitch_type IN ('fastball', 'sinker', 'cutter') THEN pr.talent_grade END) AS fastball_grade,
    AVG(CASE WHEN pr.pitch_type IN ('slider', 'curveball', 'knucklecurve') THEN pr.talent_grade END) AS breaking_grade,
    AVG(CASE WHEN pr.pitch_type IN ('changeup', 'splitter', 'forkball', 'circlechange', 'knuckleball', 'screwball') THEN pr.talent_grade END) AS offspeed_grade
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

  -- Potential percentiles (ticket 0086): target's *_talent value/grade,
  -- ranked against the same current-population CTEs above. stamina/hold/
  -- velocity have no talent counterpart in players_pitching_talent, so
  -- they get no *_potential column. LEFT JOINed below -- a missing
  -- talent row degrades to NULL, same convention as the other percentile
  -- queries.
  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM value_filtered
      WHERE pitching_runs < target_val_talent.pitching_runs AND pitching_runs IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM value_filtered WHERE pitching_runs IS NOT NULL
    )
   ) AS pitching_runs_percentile_potential,

  CASE WHEN target_cat_talent.fastball_grade IS NOT NULL THEN ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM pitch_category_filtered
      WHERE fastball_grade < target_cat_talent.fastball_grade AND fastball_grade IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM pitch_category_filtered WHERE fastball_grade IS NOT NULL
    )
   ) END AS fastball_grade_percentile_potential,

  CASE WHEN target_cat_talent.breaking_grade IS NOT NULL THEN ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM pitch_category_filtered
      WHERE breaking_grade < target_cat_talent.breaking_grade AND breaking_grade IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM pitch_category_filtered WHERE breaking_grade IS NOT NULL
    )
   ) END AS breaking_grade_percentile_potential,

  CASE WHEN target_cat_talent.offspeed_grade IS NOT NULL THEN ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM pitch_category_filtered
      WHERE offspeed_grade < target_cat_talent.offspeed_grade AND offspeed_grade IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM pitch_category_filtered WHERE offspeed_grade IS NOT NULL
    )
   ) END AS offspeed_grade_percentile_potential,

  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM value_filtered
      WHERE baserunning_runs < target_val_talent.baserunning_runs AND baserunning_runs IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM value_filtered WHERE baserunning_runs IS NOT NULL
    )
   ) AS baserunning_runs_percentile_potential,

  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM value_filtered
      WHERE total_runs < target_val_talent.total_runs AND total_runs IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM value_filtered WHERE total_runs IS NOT NULL
    )
   ) AS total_runs_percentile_potential,

  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM value_filtered
      WHERE WAR < target_val_talent.WAR AND WAR IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM value_filtered WHERE WAR IS NOT NULL
    )
   ) AS war_percentile_potential,

  -- Projection based potential percentiles (lower ERA/BA/wOBA-against is
  -- better -- comparisons inverted, same direction as the current ones).
  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM expected_filtered
      WHERE ERA > target_exp_talent.ERA AND ERA IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM expected_filtered WHERE ERA IS NOT NULL
    )
   ) AS era_percentile_potential,

  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM expected_filtered
      WHERE BA > target_exp_talent.BA AND BA IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM expected_filtered WHERE BA IS NOT NULL
    )
   ) AS xba_percentile_potential,

  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM expected_filtered
      WHERE wOBA > target_exp_talent.wOBA AND wOBA IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM expected_filtered WHERE wOBA IS NOT NULL
    )
   ) AS xwoba_percentile_potential,

  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM ratings_filtered
      WHERE stuff < target_rate_talent.stuff AND stuff IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM ratings_filtered WHERE stuff IS NOT NULL
    )
   ) AS stuff_percentile_potential,

  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM ratings_filtered
      WHERE control < target_rate_talent.control AND control IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM ratings_filtered WHERE control IS NOT NULL
    )
   ) AS control_percentile_potential,

  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM ratings_filtered
      WHERE pbabip < target_rate_talent.pbabip AND pbabip IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM ratings_filtered WHERE pbabip IS NOT NULL
    )
   ) AS pbabip_percentile_potential,

  ROUND(
    (
      SELECT COUNT(*) * 1.0
      FROM ratings_filtered
      WHERE hra < target_rate_talent.hra AND hra IS NOT NULL
    ) * 100  /
    (
      SELECT COUNT(*) FROM ratings_filtered WHERE hra IS NOT NULL
    )
   ) AS hra_percentile_potential,

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
  target_exp.wOBA AS xwoba_value,

  -- Unlike the other raw ratings (stuff/control/pbabip/hra), velocity's
  -- 1-20 index IS meant to represent a real physical quantity (OOTP's own
  -- velocity-band convention) rather than an abstract 20-80 grade borrowing
  -- an unrelated outcome-stat's name -- so it gets a raw value too, mapped
  -- to an MPH band in the frontend (PitcherPercentiles.vue's VELOCITY_MAP).
  target_rate.velocity AS velocity_value,

  target_val_talent.pitching_runs AS pitching_runs_value_potential,
  target_exp_talent.ERA AS era_value_potential,
  target_exp_talent.BA AS xba_value_potential,
  target_exp_talent.wOBA AS xwoba_value_potential

FROM players_pitching_expected AS target_exp
JOIN players_pitching AS target_rate ON target_exp.rating_id = target_rate.rating_id
JOIN players_pitching_run_value AS target_val ON target_exp.rating_id = target_val.rating_id
LEFT JOIN target_cat ON target_exp.rating_id = target_cat.rating_id
LEFT JOIN target_cat_talent ON target_exp.rating_id = target_cat_talent.rating_id
LEFT JOIN players_pitching_expected_talent AS target_exp_talent ON target_exp.rating_id = target_exp_talent.rating_id
LEFT JOIN players_pitching_run_value_talent AS target_val_talent ON target_exp.rating_id = target_val_talent.rating_id
LEFT JOIN players_pitching_talent AS target_rate_talent ON target_exp.rating_id = target_rate_talent.rating_id
WHERE target_exp.rating_id = %(rating_id)s;
