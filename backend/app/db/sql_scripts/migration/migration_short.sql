USE ootp;

INSERT IGNORE INTO players_rating (player_id, rating_date, league_id)
SELECT
    p.player_id,
    '{{HEAP_DATE}}',  
    COALESCE(t.league_id, 203) AS league_id
FROM staging.players AS p
LEFT JOIN staging.teams AS t ON p.team_id = t.team_id
WHERE p.retired = 0;

-- Excludes pitchers (ticket 0030) -- staging.players_batting has a row for
-- every player in the league, not just hitters, and carries the same
-- role code as staging.players_pitching (11/12/13 = SP/RP/Closer, 0 =
-- non-pitcher; confirmed against a real dump export: position=1/Pitcher
-- pairs with role 11/12/13 in 63,160 of 63,163 such rows). Filtering here
-- on staging's role -- not ootp.players.position -- deliberately avoids
-- the position-normalization timing gap noted in 0030's Design choices
-- (ootp.players.position only gets converted from OOTP's raw numeric codes
-- to letter codes by a later UPDATE in this same script, so a
-- newly-inserted player can still read as numeric '1' rather than 'P' at
-- this point in a run). No TWP (two-way player) carve-out -- see 0030.
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
WHERE r.rating_date = '{{HEAP_DATE}}' AND s.role NOT IN (11, 12, 13);

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
WHERE r.rating_date = '{{HEAP_DATE}}' AND s.role NOT IN (11, 12, 13);

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

-- One row per pitch type actually thrown (grade > 0), not a fixed
-- 12-column-wide row -- see ticket 0029/0031/0032's Design choices.
INSERT IGNORE INTO players_pitch_repertoire (rating_id, pitch_type, grade, talent_grade)
SELECT r.rating_id, 'fastball', s.pitching_ratings_pitches_fastball, s.pitching_ratings_pitches_talent_fastball
FROM players_rating AS r
JOIN staging.players_pitching AS s ON r.player_id = s.player_id
WHERE r.rating_date = '{{HEAP_DATE}}' AND s.role IN (11, 12, 13) AND s.pitching_ratings_pitches_fastball > 0
UNION ALL
SELECT r.rating_id, 'slider', s.pitching_ratings_pitches_slider, s.pitching_ratings_pitches_talent_slider
FROM players_rating AS r
JOIN staging.players_pitching AS s ON r.player_id = s.player_id
WHERE r.rating_date = '{{HEAP_DATE}}' AND s.role IN (11, 12, 13) AND s.pitching_ratings_pitches_slider > 0
UNION ALL
SELECT r.rating_id, 'curveball', s.pitching_ratings_pitches_curveball, s.pitching_ratings_pitches_talent_curveball
FROM players_rating AS r
JOIN staging.players_pitching AS s ON r.player_id = s.player_id
WHERE r.rating_date = '{{HEAP_DATE}}' AND s.role IN (11, 12, 13) AND s.pitching_ratings_pitches_curveball > 0
UNION ALL
SELECT r.rating_id, 'screwball', s.pitching_ratings_pitches_screwball, s.pitching_ratings_pitches_talent_screwball
FROM players_rating AS r
JOIN staging.players_pitching AS s ON r.player_id = s.player_id
WHERE r.rating_date = '{{HEAP_DATE}}' AND s.role IN (11, 12, 13) AND s.pitching_ratings_pitches_screwball > 0
UNION ALL
SELECT r.rating_id, 'forkball', s.pitching_ratings_pitches_forkball, s.pitching_ratings_pitches_talent_forkball
FROM players_rating AS r
JOIN staging.players_pitching AS s ON r.player_id = s.player_id
WHERE r.rating_date = '{{HEAP_DATE}}' AND s.role IN (11, 12, 13) AND s.pitching_ratings_pitches_forkball > 0
UNION ALL
SELECT r.rating_id, 'changeup', s.pitching_ratings_pitches_changeup, s.pitching_ratings_pitches_talent_changeup
FROM players_rating AS r
JOIN staging.players_pitching AS s ON r.player_id = s.player_id
WHERE r.rating_date = '{{HEAP_DATE}}' AND s.role IN (11, 12, 13) AND s.pitching_ratings_pitches_changeup > 0
UNION ALL
SELECT r.rating_id, 'sinker', s.pitching_ratings_pitches_sinker, s.pitching_ratings_pitches_talent_sinker
FROM players_rating AS r
JOIN staging.players_pitching AS s ON r.player_id = s.player_id
WHERE r.rating_date = '{{HEAP_DATE}}' AND s.role IN (11, 12, 13) AND s.pitching_ratings_pitches_sinker > 0
UNION ALL
SELECT r.rating_id, 'splitter', s.pitching_ratings_pitches_splitter, s.pitching_ratings_pitches_talent_splitter
FROM players_rating AS r
JOIN staging.players_pitching AS s ON r.player_id = s.player_id
WHERE r.rating_date = '{{HEAP_DATE}}' AND s.role IN (11, 12, 13) AND s.pitching_ratings_pitches_splitter > 0
UNION ALL
SELECT r.rating_id, 'knuckleball', s.pitching_ratings_pitches_knuckleball, s.pitching_ratings_pitches_talent_knuckleball
FROM players_rating AS r
JOIN staging.players_pitching AS s ON r.player_id = s.player_id
WHERE r.rating_date = '{{HEAP_DATE}}' AND s.role IN (11, 12, 13) AND s.pitching_ratings_pitches_knuckleball > 0
UNION ALL
SELECT r.rating_id, 'cutter', s.pitching_ratings_pitches_cutter, s.pitching_ratings_pitches_talent_cutter
FROM players_rating AS r
JOIN staging.players_pitching AS s ON r.player_id = s.player_id
WHERE r.rating_date = '{{HEAP_DATE}}' AND s.role IN (11, 12, 13) AND s.pitching_ratings_pitches_cutter > 0
UNION ALL
SELECT r.rating_id, 'circlechange', s.pitching_ratings_pitches_circlechange, s.pitching_ratings_pitches_talent_circlechange
FROM players_rating AS r
JOIN staging.players_pitching AS s ON r.player_id = s.player_id
WHERE r.rating_date = '{{HEAP_DATE}}' AND s.role IN (11, 12, 13) AND s.pitching_ratings_pitches_circlechange > 0
UNION ALL
SELECT r.rating_id, 'knucklecurve', s.pitching_ratings_pitches_knucklecurve, s.pitching_ratings_pitches_talent_knucklecurve
FROM players_rating AS r
JOIN staging.players_pitching AS s ON r.player_id = s.player_id
WHERE r.rating_date = '{{HEAP_DATE}}' AND s.role IN (11, 12, 13) AND s.pitching_ratings_pitches_knucklecurve > 0;

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
