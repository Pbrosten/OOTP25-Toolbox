SELECT
    cp.year,
    t.abbr,
    SUM(cp.w) AS w,
    SUM(cp.l) AS l,
    SUM(cp.s) AS s,
    SUM(cp.g) AS g,
    SUM(cp.gs) AS gs,
    SUM(cp.outs) AS outs,
    SUM(cp.k) AS k,
    SUM(cp.bb) AS bb,
    SUM(cp.ha) AS ha,
    SUM(cp.er) AS er
FROM players_career_pitching_stats cp
LEFT JOIN teams t ON cp.team_id = t.team_id
WHERE cp.player_id = %s
  AND cp.split_id = 1
  AND cp.league_id != 203
GROUP BY cp.year, t.abbr
ORDER BY cp.year DESC;
