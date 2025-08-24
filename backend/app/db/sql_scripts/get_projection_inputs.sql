SELECT 
    p.player_id, p.birth_date, p.position, p.bats, p.prone_overall,
    r.rating_id, r.rating_date,
    b.babip, b.gap, b.eye, b.strikeouts, b.power,
    bp.speed, bp.steal, bp.baserunning,
    d.pos1, d.pos2, d.pos3, d.pos4, d.pos5, d.pos6, d.pos7, d.pos8, d.pos9
FROM players AS p
JOIN players_rating as r ON p.player_id = r.player_id
JOIN players_batting as b ON r.rating_id = b.rating_id
JOIN players_basepath as bp ON r.rating_id = bp.rating_id
JOIN players_fielding_position as d ON r.rating_id = d.rating_id
WHERE r.rating_date='{{HEAP_DATE}}';