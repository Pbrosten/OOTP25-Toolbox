SELECT
    r.rating_id,
    pp.role, pp.stuff, pp.control, pp.pbabip, pp.hra, pp.stamina, pp.hold,
    p.prone_overall
FROM players AS p
JOIN players_rating AS r ON p.player_id = r.player_id
JOIN players_pitching AS pp ON r.rating_id = pp.rating_id
WHERE r.rating_date = '{{HEAP_DATE}}';
