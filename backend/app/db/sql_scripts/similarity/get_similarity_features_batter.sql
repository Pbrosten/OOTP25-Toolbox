SELECT 
    p.player_id,
    pb.babip,
    pb.gap,
    pb.power,
    pb.eye,
    pb.strikeouts,
    pb2.speed,
    pb2.steal,
    pb2.baserunning,
    p.position,
    CASE 
        WHEN p.position = 'C' THEN pf.catcher_framing
        WHEN p.position IN ('1B', '2B', 'SS') THEN pf.infield_range
        WHEN p.position = '3B' THEN pf.infield_arm
        WHEN p.position IN ('LF', 'CF', 'RF') THEN pf.outfield_range
        ELSE 20
    END AS defensive_primary,
    CASE 
        WHEN p.position = 'C' THEN pf.catcher_arm
        WHEN p.position = '1B' THEN pf.infield_error
        WHEN p.position = '2B' THEN pf.infield_doubleplay
        WHEN p.position = 'SS' THEN pf.infield_arm
        WHEN p.position = '3B' THEN pf.infield_range
        WHEN p.position IN ('LF', 'CF', 'RF') THEN pf.outfield_arm
        ELSE 20
    END AS defensive_secondary
FROM players_rating AS pr
JOIN players AS p ON pr.player_id = p.player_id
JOIN players_batting AS pb ON pr.rating_id = pb.rating_id
JOIN players_basepath AS pb2 ON pr.rating_id = pb2.rating_id
JOIN players_fielding AS pf ON pr.rating_id = pf.rating_id
JOIN teams AS t ON p.team_id = t.team_id
WHERE pr.rating_date = '2027-12-1' AND t.league_id = 203 AND p.position != 'P'