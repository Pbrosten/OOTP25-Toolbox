USE ootp;

INSERT IGNORE INTO players_rating (player_id, rating_date, league_id)
SELECT
    p.player_id,
    '{{HEAP_DATE}}',
    COALESCE(t.league_id, 203) AS league_id
FROM staging.players AS p
LEFT JOIN staging.teams AS t ON p.team_id = t.team_id
WHERE p.retired = 0;

-- Two-way players (ticket 0067): a player counts as TWP if they had real
-- usage on both sides *last* year (any PA and any IP > 0, in
-- players_career_batting_stats/players_career_pitching_stats -- already
-- ingested by migration_long.sql from a yearly heap, not staging). Uses
-- the *previous* year deliberately, not the current one: within a given
-- calendar year's dump heaps, that year's monthly heaps (01-12) are
-- processed before that same year's own yearly heap -- confirmed against
-- a real post-close-correction run: after fully reprocessing a save,
-- players_career_batting_stats/players_career_pitching_stats had real
-- 2029 rows, but a monthly 2029 heap's twp_player_ids still needs to look
-- at 2028, since 2029's own career-stat rows aren't written until the
-- "2029 yearly" heap runs, which comes *after* 2029's monthly heaps in
-- processing order (the yearly heap captures the just-completed season).
-- Checking the current year here would always find nothing.
--
-- OOTP's own per-heap `role` field toggles between a real pitcher role
-- (11/12/13) and 0 (non-pitcher) for a TWP depending on which side of
-- their game was recently emphasized -- confirmed against a real dump
-- export (a TWP's December players_pitching.mysql.sql row read role = 0
-- despite him pitching 8 IP that season). Without this carve-out, the
-- role IN/NOT IN filters below silently drop a TWP's ratings on whichever
-- side isn't currently emphasized that month.
DROP TEMPORARY TABLE IF EXISTS twp_player_ids;
CREATE TEMPORARY TABLE twp_player_ids (player_id INT PRIMARY KEY);
INSERT INTO twp_player_ids
SELECT DISTINCT cb.player_id
FROM players_career_batting_stats cb
JOIN players_career_pitching_stats cp
  ON cp.player_id = cb.player_id AND cp.year = cb.year
WHERE cb.year = YEAR('{{HEAP_DATE}}') - 1 AND cb.pa > 0 AND cp.ip > 0;

-- Excludes pitchers (ticket 0030) -- staging.players_batting has a row for
-- every player in the league, not just hitters, and carries the same
-- role code as staging.players_pitching (11/12/13 = SP/RP/Closer, 0 =
-- non-pitcher -- confirmed against a real dump export: position=1/Pitcher
-- pairs with role 11/12/13 in 63,160 of 63,163 such rows). Filtering here
-- on staging's role -- not ootp.players.position -- deliberately avoids
-- the position-normalization timing gap noted in 0030's Design choices
-- (ootp.players.position only gets converted from OOTP's raw numeric codes
-- to letter codes by a later UPDATE in this same script, so a
-- newly-inserted player can still read as numeric '1' rather than 'P' at
-- this point in a run). TWP carve-out added in ticket 0067 -- a detected
-- TWP's batting ratings are kept even in a month where their role reads
-- as a pitcher role (11/12/13), instead of being dropped.
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
WHERE r.rating_date = '{{HEAP_DATE}}'
  AND (s.role NOT IN (11, 12, 13) OR s.player_id IN (SELECT player_id FROM twp_player_ids));

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
WHERE r.rating_date = '{{HEAP_DATE}}'
  AND (s.role NOT IN (11, 12, 13) OR s.player_id IN (SELECT player_id FROM twp_player_ids));

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
-- dump export. TWP carve-out added in ticket 0067 -- a detected TWP's
-- pitching ratings are kept even in a month where their role reads 0
-- (non-pitcher), instead of being dropped -- see PitcherProjection's
-- ROLE_MAP (pitcher.py) for how role 0 is then handled at projection time.
WHERE r.rating_date = '{{HEAP_DATE}}'
  AND (s.role IN (11, 12, 13) OR s.player_id IN (SELECT player_id FROM twp_player_ids));

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
WHERE r.rating_date = '{{HEAP_DATE}}'
  AND (s.role IN (11, 12, 13) OR s.player_id IN (SELECT player_id FROM twp_player_ids));

-- One row per pitch type actually thrown (grade > 0), not a fixed
-- 12-column-wide row -- see ticket 0029/0031/0032's Design choices.
INSERT IGNORE INTO players_pitch_repertoire (rating_id, pitch_type, grade, talent_grade)
SELECT r.rating_id, 'fastball', s.pitching_ratings_pitches_fastball, s.pitching_ratings_pitches_talent_fastball
FROM players_rating AS r
JOIN staging.players_pitching AS s ON r.player_id = s.player_id
WHERE r.rating_date = '{{HEAP_DATE}}' AND (s.role IN (11, 12, 13) OR s.player_id IN (SELECT player_id FROM twp_player_ids)) AND s.pitching_ratings_pitches_fastball > 0
UNION ALL
SELECT r.rating_id, 'slider', s.pitching_ratings_pitches_slider, s.pitching_ratings_pitches_talent_slider
FROM players_rating AS r
JOIN staging.players_pitching AS s ON r.player_id = s.player_id
WHERE r.rating_date = '{{HEAP_DATE}}' AND (s.role IN (11, 12, 13) OR s.player_id IN (SELECT player_id FROM twp_player_ids)) AND s.pitching_ratings_pitches_slider > 0
UNION ALL
SELECT r.rating_id, 'curveball', s.pitching_ratings_pitches_curveball, s.pitching_ratings_pitches_talent_curveball
FROM players_rating AS r
JOIN staging.players_pitching AS s ON r.player_id = s.player_id
WHERE r.rating_date = '{{HEAP_DATE}}' AND (s.role IN (11, 12, 13) OR s.player_id IN (SELECT player_id FROM twp_player_ids)) AND s.pitching_ratings_pitches_curveball > 0
UNION ALL
SELECT r.rating_id, 'screwball', s.pitching_ratings_pitches_screwball, s.pitching_ratings_pitches_talent_screwball
FROM players_rating AS r
JOIN staging.players_pitching AS s ON r.player_id = s.player_id
WHERE r.rating_date = '{{HEAP_DATE}}' AND (s.role IN (11, 12, 13) OR s.player_id IN (SELECT player_id FROM twp_player_ids)) AND s.pitching_ratings_pitches_screwball > 0
UNION ALL
SELECT r.rating_id, 'forkball', s.pitching_ratings_pitches_forkball, s.pitching_ratings_pitches_talent_forkball
FROM players_rating AS r
JOIN staging.players_pitching AS s ON r.player_id = s.player_id
WHERE r.rating_date = '{{HEAP_DATE}}' AND (s.role IN (11, 12, 13) OR s.player_id IN (SELECT player_id FROM twp_player_ids)) AND s.pitching_ratings_pitches_forkball > 0
UNION ALL
SELECT r.rating_id, 'changeup', s.pitching_ratings_pitches_changeup, s.pitching_ratings_pitches_talent_changeup
FROM players_rating AS r
JOIN staging.players_pitching AS s ON r.player_id = s.player_id
WHERE r.rating_date = '{{HEAP_DATE}}' AND (s.role IN (11, 12, 13) OR s.player_id IN (SELECT player_id FROM twp_player_ids)) AND s.pitching_ratings_pitches_changeup > 0
UNION ALL
SELECT r.rating_id, 'sinker', s.pitching_ratings_pitches_sinker, s.pitching_ratings_pitches_talent_sinker
FROM players_rating AS r
JOIN staging.players_pitching AS s ON r.player_id = s.player_id
WHERE r.rating_date = '{{HEAP_DATE}}' AND (s.role IN (11, 12, 13) OR s.player_id IN (SELECT player_id FROM twp_player_ids)) AND s.pitching_ratings_pitches_sinker > 0
UNION ALL
SELECT r.rating_id, 'splitter', s.pitching_ratings_pitches_splitter, s.pitching_ratings_pitches_talent_splitter
FROM players_rating AS r
JOIN staging.players_pitching AS s ON r.player_id = s.player_id
WHERE r.rating_date = '{{HEAP_DATE}}' AND (s.role IN (11, 12, 13) OR s.player_id IN (SELECT player_id FROM twp_player_ids)) AND s.pitching_ratings_pitches_splitter > 0
UNION ALL
SELECT r.rating_id, 'knuckleball', s.pitching_ratings_pitches_knuckleball, s.pitching_ratings_pitches_talent_knuckleball
FROM players_rating AS r
JOIN staging.players_pitching AS s ON r.player_id = s.player_id
WHERE r.rating_date = '{{HEAP_DATE}}' AND (s.role IN (11, 12, 13) OR s.player_id IN (SELECT player_id FROM twp_player_ids)) AND s.pitching_ratings_pitches_knuckleball > 0
UNION ALL
SELECT r.rating_id, 'cutter', s.pitching_ratings_pitches_cutter, s.pitching_ratings_pitches_talent_cutter
FROM players_rating AS r
JOIN staging.players_pitching AS s ON r.player_id = s.player_id
WHERE r.rating_date = '{{HEAP_DATE}}' AND (s.role IN (11, 12, 13) OR s.player_id IN (SELECT player_id FROM twp_player_ids)) AND s.pitching_ratings_pitches_cutter > 0
UNION ALL
SELECT r.rating_id, 'circlechange', s.pitching_ratings_pitches_circlechange, s.pitching_ratings_pitches_talent_circlechange
FROM players_rating AS r
JOIN staging.players_pitching AS s ON r.player_id = s.player_id
WHERE r.rating_date = '{{HEAP_DATE}}' AND (s.role IN (11, 12, 13) OR s.player_id IN (SELECT player_id FROM twp_player_ids)) AND s.pitching_ratings_pitches_circlechange > 0
UNION ALL
SELECT r.rating_id, 'knucklecurve', s.pitching_ratings_pitches_knucklecurve, s.pitching_ratings_pitches_talent_knucklecurve
FROM players_rating AS r
JOIN staging.players_pitching AS s ON r.player_id = s.player_id
WHERE r.rating_date = '{{HEAP_DATE}}' AND (s.role IN (11, 12, 13) OR s.player_id IN (SELECT player_id FROM twp_player_ids)) AND s.pitching_ratings_pitches_knucklecurve > 0;

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
