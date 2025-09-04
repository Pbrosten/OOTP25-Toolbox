ATTACH DATABASE '{{STAGGING_DB_PATH}}' AS stage;

-- injection scripts
INSERT OR IGNORE INTO players(player_id, first_name, last_name, birth_date,
position, height, weight, bats, throws, free_agent, team_id, prone_overall)
SELECT
    player_id,
    first_name,
    last_name,
    date_of_birth,
    position,
    height,
    weight,
    bats,
    throws,
    free_agent,
    team_id,
    prone_overall
FROM stage.players
WHERE retired = 0;

INSERT OR IGNORE INTO players_rating(player_id, rating_date)
SELECT
    player_id,
    '{{HEAP_DATE}}'
FROM stage.players
WHERE retired = 0;

INSERT OR IGNORE INTO players_batting
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
JOIN stage.players_batting AS s ON r.player_id = s.player_id;

INSERT OR IGNORE INTO players_batting_talent
SELECT
    r.rating_id,
    s.batting_ratings_talent_contact,
    s.batting_ratings_talent_gap,
    s.batting_ratings_talent_eye,
    s.batting_ratings_talent_strikeouts,
    s.batting_ratings_talent_power,
    s.batting_ratings_talent_babip
FROM players_rating AS r
JOIN stage.players_batting AS s ON r.player_id = s.player_id;

INSERT OR IGNORE INTO players_basepath
SELECT
    r.rating_id,
    s.running_ratings_speed,
    s.running_ratings_stealing_rate,
    s.running_ratings_stealing,
    s.running_ratings_baserunning
FROM players_rating AS r
JOIN stage.players_batting AS s ON r.player_id = s.player_id;

INSERT OR IGNORE INTO players_fielding_position
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
FROM players_rating as r
JOIN stage.players_fielding AS s ON r.player_id = s.player_id;

INSERT OR IGNORE INTO players_fielding_position_talent
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
FROM players_rating as r
JOIN stage.players_fielding AS s ON r.player_id = s.player_id;

INSERT OR IGNORE INTO players_fielding
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
FROM players_rating as r
JOIN stage.players_fielding AS s ON r.player_id = s.player_id;

-- data transform scripts
--- players table
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

DETACH DATABASE stage;