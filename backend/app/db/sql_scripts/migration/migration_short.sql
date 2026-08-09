USE ootp;

INSERT IGNORE INTO players_rating (player_id, rating_date, league_id)
SELECT
    p.player_id,
    '{{HEAP_DATE}}',  
    COALESCE(t.league_id, 203) AS league_id
FROM staging.players AS p
LEFT JOIN staging.teams AS t ON p.team_id = t.team_id
WHERE p.retired = 0;

INSERT IGNORE INTO players_batting (
    rating_id, contact, gap, eye, strikeouts, power, babip, bunt, bunt_for_hit
)
SELECT
    r.rating_id,
    s.batting_ratings_overall_contact,
    s.batting_ratings_overall_gap,
    s.batting_ratings_overall_eye,
    s.batting_ratings_overall_strikeouts,
    s.batting_ratings_overall_power,
    s.batting_ratings_overall_babip,
    s.batting_ratings_misc_bunt,
    s.batting_ratings_misc_bunt_for_hit
FROM players_rating AS r
JOIN staging.players_batting AS s ON r.player_id = s.player_id
WHERE r.rating_date = '{{HEAP_DATE}}';

INSERT IGNORE INTO players_batting_talent (
    rating_id, contact, gap, eye, strikeouts, power, babip
)
SELECT
    r.rating_id,
    s.batting_ratings_talent_contact,
    s.batting_ratings_talent_gap,
    s.batting_ratings_talent_eye,
    s.batting_ratings_talent_strikeouts,
    s.batting_ratings_talent_power,
    s.batting_ratings_talent_babip
FROM players_rating AS r
JOIN staging.players_batting AS s ON r.player_id = s.player_id
WHERE r.rating_date = '{{HEAP_DATE}}';

INSERT IGNORE INTO players_pitching (
    rating_id, role, stuff, movement, hra, pbabip, control, balk, hp, wild_pitch,
    velocity, arm_slot, stamina, ground_fly, hold
)
SELECT
    r.rating_id,
    s.role,
    s.pitching_ratings_overall_stuff,
    s.pitching_ratings_overall_movement,
    s.pitching_ratings_overall_hra,
    s.pitching_ratings_overall_pbabip,
    s.pitching_ratings_overall_control,
    s.pitching_ratings_overall_balk,
    s.pitching_ratings_overall_hp,
    s.pitching_ratings_overall_wild_pitch,
    s.pitching_ratings_misc_velocity,
    s.pitching_ratings_misc_arm_slot,
    s.pitching_ratings_misc_stamina,
    s.pitching_ratings_misc_ground_fly,
    s.pitching_ratings_misc_hold
FROM players_rating AS r
JOIN staging.players_pitching AS s ON r.player_id = s.player_id
-- staging.players_pitching has one row per player in the league (not just
-- pitchers) -- role 11/12/13 = SP/RP/Closer, role 0 = non-pitcher. See
-- ticket 0026's Design choices for how this was confirmed against a real
-- dump export.
WHERE r.rating_date = '{{HEAP_DATE}}' AND s.role IN (11, 12, 13);

INSERT IGNORE INTO players_pitching_talent (
    rating_id, stuff, movement, hra, pbabip, control, balk, hp, wild_pitch
)
SELECT
    r.rating_id,
    s.pitching_ratings_talent_stuff,
    s.pitching_ratings_talent_movement,
    s.pitching_ratings_talent_hra,
    s.pitching_ratings_talent_pbabip,
    s.pitching_ratings_talent_control,
    s.pitching_ratings_talent_balk,
    s.pitching_ratings_talent_hp,
    s.pitching_ratings_talent_wild_pitch
FROM players_rating AS r
JOIN staging.players_pitching AS s ON r.player_id = s.player_id
WHERE r.rating_date = '{{HEAP_DATE}}' AND s.role IN (11, 12, 13);

INSERT IGNORE INTO players_basepath (
    rating_id, speed, steal_rate, steal, baserunning
)
SELECT
    r.rating_id,
    s.running_ratings_speed,
    s.running_ratings_stealing_rate,
    s.running_ratings_stealing,
    s.running_ratings_baserunning
FROM players_rating AS r
JOIN staging.players_batting AS s ON r.player_id = s.player_id
WHERE r.rating_date = '{{HEAP_DATE}}';

INSERT IGNORE INTO players_fielding (
    rating_id,
    catcher_arm, catcher_ability, catcher_framing,
    infield_range, infield_arm, infield_doubleplay, infield_error,
    outfield_range, outfield_arm, outfield_error
)
SELECT
    r.rating_id,
    s.fielding_ratings_catcher_arm,
    s.fielding_ratings_catcher_ability,
    s.fielding_ratings_catcher_framing,
    s.fielding_ratings_infield_range,
    s.fielding_ratings_infield_arm,
    s.fielding_ratings_turn_doubleplay,
    s.fielding_ratings_infield_error,
    s.fielding_ratings_outfield_range,
    s.fielding_ratings_outfield_arm,
    s.fielding_ratings_outfield_error
FROM players_rating AS r
JOIN staging.players_fielding AS s ON r.player_id = s.player_id
WHERE r.rating_date = '{{HEAP_DATE}}';

INSERT IGNORE INTO players_fielding_position (
    rating_id, pos1, pos2, pos3, pos4, pos5, pos6, pos7, pos8, pos9
)
SELECT
    r.rating_id,
    s.fielding_rating_pos1,
    s.fielding_rating_pos2,
    s.fielding_rating_pos3,
    s.fielding_rating_pos4,
    s.fielding_rating_pos5,
    s.fielding_rating_pos6,
    s.fielding_rating_pos7,
    s.fielding_rating_pos8,
    s.fielding_rating_pos9
FROM players_rating AS r
JOIN staging.players_fielding AS s ON r.player_id = s.player_id
WHERE r.rating_date = '{{HEAP_DATE}}';

INSERT IGNORE INTO players_fielding_position_talent (
    rating_id, pos1, pos2, pos3, pos4, pos5, pos6, pos7, pos8, pos9
)
SELECT
    r.rating_id,
    s.fielding_rating_pos1_pot,
    s.fielding_rating_pos2_pot,
    s.fielding_rating_pos3_pot,
    s.fielding_rating_pos4_pot,
    s.fielding_rating_pos5_pot,
    s.fielding_rating_pos6_pot,
    s.fielding_rating_pos7_pot,
    s.fielding_rating_pos8_pot,
    s.fielding_rating_pos9_pot
FROM players_rating AS r
JOIN staging.players_fielding AS s ON r.player_id = s.player_id
WHERE r.rating_date = '{{HEAP_DATE}}';

UPDATE players
SET position = CASE position
    WHEN '1' THEN 'P'
    WHEN '2' THEN 'C'
    WHEN '3' THEN '1B'
    WHEN '4' THEN '2B'
    WHEN '5' THEN '3B'
    WHEN '6' THEN 'SS'
    WHEN '7' THEN 'LF'
    WHEN '8' THEN 'CF'
    WHEN '9' THEN 'RF'
    WHEN '10' THEN 'DH'
    ELSE position
END;

UPDATE players
SET bats = CASE bats
    WHEN '1' THEN 'R'
    WHEN '2' THEN 'L'
    WHEN '3' THEN 'S'
    ELSE bats
END;

UPDATE players
SET throws = CASE throws
    WHEN '1' THEN 'R'
    WHEN '2' THEN 'L'
    ELSE throws
END;
