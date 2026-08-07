SELECT
    cb.year,
    t.abbr,
    SUM(cb.ab) AS ab,
    SUM(cb.h) AS h,
    SUM(cb.pa) AS pa,
    SUM(cb.r) AS r,
    SUM(cb.hr) AS hr,
    SUM(cb.sb) AS sb,
    SUM(cb.bb) AS bb,
    SUM(cb.hp) AS hp,
    SUM(cb.sf) AS sf,
    SUM(cb.d) AS d,
    SUM(cb.t) AS t
FROM players_career_batting_stats cb
LEFT JOIN teams t ON cb.team_id = t.team_id
WHERE cb.player_id = %s
  AND cb.split_id = 1
  AND cb.league_id = 203
GROUP BY cb.year, t.abbr
ORDER BY cb.year DESC;