SELECT
    p.first_name,
    p.last_name,
    p.position,
    -- is_twp (ticket 0067): a two-way player -- real PA and IP in the same
    -- season, checked against their most recent recorded career-batting
    -- year (not a hardcoded year offset, unlike migration_short.sql's
    -- pipeline-timing-constrained version of this same check -- this runs
    -- at request time, not heap-processing time, so it can just ask "was
    -- he two-way in his own latest season on record"). p.position stays
    -- untouched -- it still drives the batting/pitching table and
    -- BatterPercentiles/PitcherPercentiles selection elsewhere; this is a
    -- separate display-only flag, not a replacement for it.
    EXISTS (
        SELECT 1
        FROM players_career_batting_stats cb
        JOIN players_career_pitching_stats cp
          ON cp.player_id = cb.player_id AND cp.year = cb.year
        WHERE cb.player_id = p.player_id
          AND cb.year = (
              SELECT MAX(year) FROM players_career_batting_stats
              WHERE player_id = p.player_id
          )
          AND cb.pa > 0 AND cp.ip > 0
    ) AS is_twp,
    p.bats,
    p.throws,
    p.height,
    p.weight,
    p.age,
    p.retired,
    p.team_id,
    COALESCE(t.name, 'Free Agent') AS team_city,
    COALESCE(t.nickname, '') AS team_name,
    t.league_id
FROM players AS p
LEFT JOIN teams as t ON p.team_id = t.team_id
WHERE p.player_id = %s;