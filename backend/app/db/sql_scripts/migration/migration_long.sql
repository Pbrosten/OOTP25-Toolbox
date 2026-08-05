USE ootp;

INSERT IGNORE INTO teams (
    team_id, name, abbr, nickname, division_id,
    league_id, human_team, background_color, text_color
)
VALUES (
    999, 'Free Agents', 'FA', 'Free Agents',
    NULL, 203, 0, '#FFFFFF', '#000000'
);


INSERT INTO teams (
    team_id, name, abbr, nickname, division_id,
    league_id, human_team, background_color, text_color
)
SELECT 
    team_id, name, abbr, nickname, division_id,
    league_id, human_team, background_color_id, text_color_id
FROM staging.teams
ON DUPLICATE KEY UPDATE
    name = VALUES(name),
    abbr = VALUES(abbr),
    nickname = VALUES(nickname),
    division_id = VALUES(division_id),
    league_id = VALUES(league_id),
    human_team = VALUES(human_team),
    background_color = VALUES(background_color),
    text_color = VALUES(text_color);

INSERT INTO players (
    player_id, first_name, last_name, birth_date,
    position, height, weight, bats, throws,
    free_agent, team_id, prone_overall
)
SELECT 
    player_id, first_name, last_name, date_of_birth,
    position, height, weight, bats, throws,
    free_agent,
    CASE WHEN team_id = 0 THEN 999 ELSE team_id END,
    prone_overall
FROM staging.players
WHERE retired = 0
ON DUPLICATE KEY UPDATE
    team_id = VALUES(team_id),
    prone_overall = VALUES(prone_overall);

INSERT INTO players_career_batting_stats (
    player_id, year, team_id, game_id, league_id,
    level_id, split_id, ab, h, k, pa, pitches_seen,
    g, gs, d, t, hr, r, rbi, sb, cs, bb, ibb,
    gdp, sh, sf, hp, ci, wpa, stint, ubr, war
)
SELECT 
    s.player_id, s.year,
    CASE WHEN s.team_id=0 THEN 999 ELSE s.team_id END,
    s.game_id, s.league_id,
    s.level_id, s.split_id, s.ab, s.h, s.k, s.pa, s.pitches_seen,
    s.g, s.gs, s.d, s.t, s.hr, s.r, s.rbi, s.sb, s.cs, s.bb, s.ibb,
    s.gdp, s.sh, s.sf, s.hp, s.ci, s.wpa, s.stint, s.ubr, s.war
FROM staging.players_career_batting_stats s
INNER JOIN players p ON s.player_id = p.player_id
WHERE s.split_id = 1
ON DUPLICATE KEY UPDATE
    ab = VALUES(ab),
    h = VALUES(h),
    k = VALUES(k),
    pa = VALUES(pa),
    pitches_seen = VALUES(pitches_seen),
    g = VALUES(g),
    gs = VALUES(gs),
    d = VALUES(d),
    t = VALUES(t),
    hr = VALUES(hr),
    r = VALUES(r),
    rbi = VALUES(rbi),
    sb = VALUES(sb),
    cs = VALUES(cs),
    bb = VALUES(bb),
    ibb = VALUES(ibb),
    gdp = VALUES(gdp),
    sh = VALUES(sh),
    sf = VALUES(sf),
    hp = VALUES(hp),
    ci = VALUES(ci),
    wpa = VALUES(wpa),
    stint = VALUES(stint),
    ubr = VALUES(ubr),
    war = VALUES(war);
