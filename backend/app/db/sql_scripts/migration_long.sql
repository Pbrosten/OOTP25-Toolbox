ATTACH DATABASE '{{STAGGING_DB_PATH}}' AS stage;

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

INSERT OR IGNORE INTO teams(team_id, name, abbr, nickname, division_id,
league_id, human_team, background_color, text_color)
SELECT
    team_id,
    name,
    abbr,
    nickname,
    division_id,
    league_id,
    human_team,
    background_color_id,
    text_color_id
FROM stage.teams;

INSERT INTO players_career_batting_stats
SELECT
    player_id,
    year,
    team_id,
    game_id,
    league_id,
    level_id,
    split_id,
    ab,
    h,
    k,
    pa,
    pitches_seen,
    g,
    gs,
    d,
    t,
    hr,
    r,
    rbi,
    sb,
    cs,
    bb,
    ibb,
    gdp,
    sh,
    sf,
    hp,
    ci,
    wpa,
    stint,
    ubr,
    war,
FROM stage.players_career_batting_stats;