ATTACH DATABASE '{{STAGGING_DB_PATH}}' AS stage;

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