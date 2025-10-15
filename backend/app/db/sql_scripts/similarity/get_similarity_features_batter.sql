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
	pf.catcher_arm,
	pf.catcher_framing,
	pf.infield_range,
	pf.infield_arm,
	pf.infield_doubleplay,
	pf.outfield_range,
	pf.outfield_arm
FROM players_rating AS pr
JOIN players AS p on pr.player_id = p.player_id
JOIN players_batting AS pb ON pr.rating_id = pb.rating_id
JOIN players_basepath AS pb2 ON pr.rating_id = pb2.rating_id
JOIN players_fielding AS pf ON pr.rating_id = pf.rating_id
JOIN teams AS t on p.team_id = t.team_id
WHERE pr.rating_date = :rating_date AND t.league_id = 203 AND p.position != 'P'