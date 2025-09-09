SELECT
    cb.year,
    t.abbr,
    cb.league_id,
    cb.split_id,
    cb.ab,
    cb.h,
    cb.k,
    cb.pa,
    cb.g,
    cb.gs,
    cb.d,
    cb.t,
    cb.hr,
    cb.r,
    cb.rbi,
    cb.sb,
    cb.bb,
    cb.wpa,
    cb.ubr,
    cb.war
FROM players_career_batting_stats as cb
LEFT JOIN teams as t on cb.team_id = t.team_id
WHERE cb.player_id = ?;