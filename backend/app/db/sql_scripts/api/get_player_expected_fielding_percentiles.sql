WITH target_player AS (
  SELECT
    pr.rating_id,
    pr.player_id,
    pr.rating_date,
    pr.league_id,
    p.position,
    -- effective_position (ticket 0067 post-close correction): for a TWP
    -- whose listed players.position is 'P' -- not a real fielding
    -- position -- substitute their highest-graded non-pitcher fielding
    -- slot from players_fielding_position instead. Confirmed real case:
    -- Bryce Eldridge is listed 'P' but has real fielding grades (RF 60,
    -- 1B 50, LF 35) that were otherwise entirely discarded --
    -- position_group fell through to 'other', so no fielding_value or
    -- arm/range percentile was ever computed for him at all. Everyone
    -- else (a real one-way pitcher, or any non-'P' position) is
    -- unaffected -- the subquery only ever runs for position = 'P', and
    -- only picks a slot with grade > 0. This only changes which fielding
    -- cohort/value this query compares the target against -- the API's
    -- own `position` output field (and every other feature keyed off
    -- players.position) is untouched.
    -- MariaDB can't correlate a derived table (FROM-clause subquery)
    -- against an outer query column without LATERAL, so this picks the
    -- best slot via GREATEST()/CASE against a single correlated row
    -- instead of unpivoting pos2..pos9 into a derived table.
    COALESCE(
      (
        SELECT
          CASE GREATEST(
            COALESCE(pfp.pos2, 0), COALESCE(pfp.pos3, 0), COALESCE(pfp.pos4, 0),
            COALESCE(pfp.pos5, 0), COALESCE(pfp.pos6, 0), COALESCE(pfp.pos7, 0),
            COALESCE(pfp.pos8, 0), COALESCE(pfp.pos9, 0)
          )
            WHEN pfp.pos2 THEN 'C'
            WHEN pfp.pos3 THEN '1B'
            WHEN pfp.pos4 THEN '2B'
            WHEN pfp.pos5 THEN '3B'
            WHEN pfp.pos6 THEN 'SS'
            WHEN pfp.pos7 THEN 'LF'
            WHEN pfp.pos8 THEN 'CF'
            WHEN pfp.pos9 THEN 'RF'
          END
        FROM players_fielding_position pfp
        WHERE pfp.rating_id = pr.rating_id
          AND p.position = 'P'
          AND GREATEST(
                COALESCE(pfp.pos2, 0), COALESCE(pfp.pos3, 0), COALESCE(pfp.pos4, 0),
                COALESCE(pfp.pos5, 0), COALESCE(pfp.pos6, 0), COALESCE(pfp.pos7, 0),
                COALESCE(pfp.pos8, 0), COALESCE(pfp.pos9, 0)
              ) > 0
      ),
      p.position
    ) AS effective_position
  FROM players_rating pr
  JOIN players p ON pr.player_id = p.player_id
  WHERE pr.rating_id = %(rating_id)s
),

target_player_grouped AS (
  SELECT
    tp.rating_id, tp.player_id, tp.rating_date, tp.league_id, tp.position,
    CASE
      WHEN tp.effective_position = 'C' THEN 'catcher'
      WHEN tp.effective_position IN ('1B', '2B', '3B', 'SS') THEN 'infield'
      WHEN tp.effective_position IN ('LF', 'CF', 'RF') THEN 'outfield'
      WHEN tp.effective_position = 'DH' THEN 'dh'
      ELSE 'other'
    END AS position_group,
    tp.effective_position
  FROM target_player tp
),

target_value AS (
  SELECT
    tp.rating_id, tp.player_id, tp.rating_date, tp.league_id, tp.position, tp.position_group,
    CASE tp.effective_position
      WHEN 'C' THEN pfe.`C`
      WHEN '1B' THEN pfe.`1B`
      WHEN '2B' THEN pfe.`2B`
      WHEN '3B' THEN pfe.`3B`
      WHEN 'SS' THEN pfe.`SS`
      WHEN 'LF' THEN pfe.`LF`
      WHEN 'CF' THEN pfe.`CF`
      WHEN 'RF' THEN pfe.`RF`
      WHEN 'DH' THEN pfe.`DH`
    END AS fielding_value,
    -- Potential (ticket 0086): same effective_position lookup against
    -- players_fielding_expected_talent. LEFT JOINed -- a missing talent
    -- row (e.g. process_player()'s potential run failed for this rating)
    -- degrades to NULL, same convention as the other percentile queries.
    CASE tp.effective_position
      WHEN 'C' THEN pfet.`C`
      WHEN '1B' THEN pfet.`1B`
      WHEN '2B' THEN pfet.`2B`
      WHEN '3B' THEN pfet.`3B`
      WHEN 'SS' THEN pfet.`SS`
      WHEN 'LF' THEN pfet.`LF`
      WHEN 'CF' THEN pfet.`CF`
      WHEN 'RF' THEN pfet.`RF`
      WHEN 'DH' THEN pfet.`DH`
    END AS fielding_value_potential
  FROM target_player_grouped tp
  JOIN players_fielding_expected pfe ON tp.rating_id = pfe.rating_id
  LEFT JOIN players_fielding_expected_talent pfet ON tp.rating_id = pfet.rating_id
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

  -- Potential (ticket 0086): the target's talent fielding_value, ranked
  -- against the same current-population `cohort` CTE above. No potential
  -- data exists for the catcher_arm/infield_arm/etc. "tool" grades below
  -- -- only the positional (pos1-pos9) grades have a talent table -- so
  -- those percentiles have no *_potential counterpart.
  CASE WHEN t.position_group = 'dh' OR t.fielding_value_potential IS NULL THEN NULL ELSE ROUND(
    100.0 * (
      SELECT COUNT(*) FROM cohort c
      WHERE c.fielding_value < t.fielding_value_potential
    ) / (
      SELECT COUNT(*) FROM cohort
    )
  ) END AS fielding_value_percentile_potential,

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
