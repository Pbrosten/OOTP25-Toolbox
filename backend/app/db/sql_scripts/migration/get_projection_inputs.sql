-- t_* columns (ticket 0086): players_batting_talent/
-- players_fielding_position_talent's ceiling grades, used to run
-- BatterProjection a second time per rating (see app/db/projection.py's
-- process_player) for the "potential" percentile bars. No basepath talent
-- table exists -- bp.speed/steal/baserunning stay shared between the
-- current and potential runs.
SELECT
    p.player_id, p.birth_date, p.position, p.bats, p.prone_overall,
    r.rating_id, r.rating_date,
    b.babip, b.gap, b.eye, b.strikeouts, b.power,
    bp.speed, bp.steal, bp.baserunning,
    d.pos1, d.pos2, d.pos3, d.pos4, d.pos5, d.pos6, d.pos7, d.pos8, d.pos9,
    bt.babip AS t_babip, bt.gap AS t_gap, bt.eye AS t_eye,
    bt.strikeouts AS t_strikeouts, bt.power AS t_power,
    dt.pos2 AS t_pos2, dt.pos3 AS t_pos3, dt.pos4 AS t_pos4,
    dt.pos5 AS t_pos5, dt.pos6 AS t_pos6, dt.pos7 AS t_pos7,
    dt.pos8 AS t_pos8, dt.pos9 AS t_pos9
FROM players AS p
JOIN players_rating as r ON p.player_id = r.player_id
JOIN players_batting as b ON r.rating_id = b.rating_id
JOIN players_basepath as bp ON r.rating_id = bp.rating_id
JOIN players_fielding_position as d ON r.rating_id = d.rating_id
JOIN players_batting_talent AS bt ON r.rating_id = bt.rating_id
JOIN players_fielding_position_talent AS dt ON r.rating_id = dt.rating_id
WHERE r.rating_date='{{HEAP_DATE}}';