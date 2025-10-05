SELECT
    p.first_name,
    p.last_name,
    p.position,
    p.bats,
    p.throws,
    p.height,
    p.weight,
    p.age,
    COALESCE(t.name, 'Free Agent') AS team_city,
    COALESCE(t.nickname, '') AS team_name,
    t.league_id
FROM players AS p
LEFT JOIN teams as t ON p.team_id = t.team_id
WHERE p.player_id = ?;