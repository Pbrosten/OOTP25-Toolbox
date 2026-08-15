WITH target_player AS (
  SELECT
    pr.rating_id,
    pr.player_id,
    pr.rating_date,
    pr.league_id,
    p.position,
    CASE
      WHEN p.position = 'C' THEN 'catcher'
      WHEN p.position IN ('1B', '2B', '3B', 'SS') THEN 'infield'
      WHEN p.position IN ('LF', 'CF', 'RF') THEN 'outfield'
      WHEN p.position = 'DH' THEN 'dh'
      ELSE 'other'
    END AS position_group
  FROM players_rating pr
  JOIN players p ON pr.player_id = p.player_id
  WHERE pr.rating_id = %(rating_id)s
),

target_value AS (
  SELECT
    tp.*,
    CASE tp.position
      WHEN 'C' THEN pfe.`C`
      WHEN '1B' THEN pfe.`1B`
      WHEN '2B' THEN pfe.`2B`
      WHEN '3B' THEN pfe.`3B`
      WHEN 'SS' THEN pfe.`SS`
      WHEN 'LF' THEN pfe.`LF`
      WHEN 'CF' THEN pfe.`CF`
      WHEN 'RF' THEN pfe.`RF`
      WHEN 'DH' THEN pfe.`DH`
    END AS fielding_value
  FROM target_player tp
  JOIN players_fielding_expected pfe ON tp.rating_id = pfe.rating_id
),

cohort AS (
  SELECT
    pr.rating_id,
    pr.player_id,
    pr.rating_date,
    pr.league_id,
    p.position,
    CASE
      WHEN p.position = 'C' THEN 'catcher'
      WHEN p.position IN ('1B', '2B', '3B', 'SS') THEN 'infield'
      WHEN p.position IN ('LF', 'CF', 'RF') THEN 'outfield'
      WHEN p.position = 'DH' THEN 'dh'
      ELSE 'other'
    END AS position_group,
    CASE p.position
      WHEN 'C' THEN pfe.`C`
      WHEN '1B' THEN pfe.`1B`
      WHEN '2B' THEN pfe.`2B`
      WHEN '3B' THEN pfe.`3B`
      WHEN 'SS' THEN pfe.`SS`
      WHEN 'LF' THEN pfe.`LF`
      WHEN 'CF' THEN pfe.`CF`
      WHEN 'RF' THEN pfe.`RF`
      WHEN 'DH' THEN pfe.`DH`
    END AS fielding_value
  FROM players_rating pr
  JOIN players p ON pr.player_id = p.player_id
  JOIN players_fielding_expected pfe ON pr.rating_id = pfe.rating_id
  JOIN target_value tv
    ON pr.rating_date = tv.rating_date
   AND pr.league_id = tv.league_id
   AND (
     CASE
       WHEN p.position = 'C' THEN 'catcher'
       WHEN p.position IN ('1B', '2B', '3B', 'SS') THEN 'infield'
       WHEN p.position IN ('LF', 'CF', 'RF') THEN 'outfield'
       WHEN p.position = 'DH' THEN 'dh'
       ELSE 'other'
     END
   ) = tv.position_group
  WHERE p.age >= 22
),

catcher_cohort AS (
  SELECT
    pr.rating_id,
    f.catcher_arm,
    f.catcher_framing
  FROM players_rating pr
  JOIN players p ON pr.player_id = p.player_id
  JOIN players_fielding f ON pr.rating_id = f.rating_id
  JOIN target_value tv
    ON pr.rating_date = tv.rating_date
   AND (
        (%(is_milb)s = 1 AND pr.league_id = tv.league_id)
        OR (%(is_milb)s = 0 AND pr.league_id = 203)
   )
  WHERE p.position = 'C' AND p.age >= 20
),

infielder_cohort AS (
  SELECT
    pr.rating_id,
    f.infield_arm,
    f.infield_range
  FROM players_rating pr
  JOIN players p ON pr.player_id = p.player_id
  JOIN players_fielding f ON pr.rating_id = f.rating_id
  JOIN target_value tv
    ON pr.rating_date = tv.rating_date
   AND (
        (%(is_milb)s = 1 AND pr.league_id = tv.league_id)
        OR (%(is_milb)s = 0 AND pr.league_id = 203)
   )
  WHERE p.position in ('1B', '2B', '3B', 'SS') AND p.age >= 22
),

outfielder_cohort AS (
  SELECT
    pr.rating_id,
    f.outfield_arm,
    f.outfield_range
  FROM players_rating pr
  JOIN players p ON pr.player_id = p.player_id
  JOIN players_fielding f ON pr.rating_id = f.rating_id
  JOIN target_value tv
    ON pr.rating_date = tv.rating_date
   AND (
        (%(is_milb)s = 1 AND pr.league_id = tv.league_id)
        OR (%(is_milb)s = 0 AND pr.league_id = 203)
   )
  WHERE p.position in ('LF', 'CF', 'RF') AND p.age >= 22
)

SELECT
  t.rating_id,
  t.position,
  t.position_group,
  -- DH has no real fielding grade -- players_fielding_expected.DH is a
  -- placeholder OOTP exports, not a genuine fielding value, so comparing
  -- DH against other DH on it is meaningless (ticket 0060).
  CASE WHEN t.position_group = 'dh' THEN NULL ELSE t.fielding_value END AS fielding_value,

  CASE WHEN t.position_group = 'dh' THEN NULL ELSE ROUND(
    100.0 * (
      SELECT COUNT(*) FROM cohort c
      WHERE c.fielding_value < t.fielding_value
    ) / (
      SELECT COUNT(*) FROM cohort
    )
  ) END AS fielding_value_percentile,

  CASE
    WHEN t.position_group = 'catcher' THEN ROUND(
      100.0 * (
        SELECT COUNT(*) FROM catcher_cohort AS c
        WHERE c.catcher_arm < f.catcher_arm
      ) / (
        SELECT COUNT(*) FROM catcher_cohort
      )
    )
    ELSE NULL
  END AS catcher_arm_percentile,

  CASE
    WHEN t.position_group = 'catcher' THEN ROUND(
      100.0 * (
        SELECT COUNT(*) FROM catcher_cohort AS c
        WHERE c.catcher_framing < f.catcher_framing
      ) / (
        SELECT COUNT(*) FROM catcher_cohort
      )
    )
    ELSE NULL
  END AS catcher_framing_percentile,

  CASE
    WHEN t.position_group = 'infield' THEN ROUND(
      100.0 * (
        SELECT COUNT(*) FROM infielder_cohort AS c
        WHERE c.infield_arm < f.infield_arm
      ) / (
        SELECT COUNT(*) FROM infielder_cohort
      )
    )
    ELSE NULL
  END AS infield_arm_percentile,

  CASE
    WHEN t.position_group = 'infield' THEN ROUND(
      100.0 * (
        SELECT COUNT(*) FROM infielder_cohort AS c
        WHERE c.infield_range < f.infield_range
      ) / (
        SELECT COUNT(*) FROM infielder_cohort
      )
    )
    ELSE NULL
  END AS infield_range_percentile,

  CASE
    WHEN t.position_group = 'outfield' THEN ROUND(
      100.0 * (
        SELECT COUNT(*) FROM outfielder_cohort AS c
        WHERE c.outfield_arm < f.outfield_arm
      ) / (
        SELECT COUNT(*) FROM outfielder_cohort
      )
    )
    ELSE NULL
  END AS outfield_arm_percentile,

  CASE
    WHEN t.position_group = 'outfield' THEN ROUND(
      100.0 * (
        SELECT COUNT(*) FROM outfielder_cohort AS c
        WHERE c.outfield_range < f.outfield_range
      ) / (
        SELECT COUNT(*) FROM outfielder_cohort
      )
    )
    ELSE NULL
  END AS outfield_range_percentile

FROM target_value t
JOIN players_fielding f ON f.rating_id = t.rating_id;
