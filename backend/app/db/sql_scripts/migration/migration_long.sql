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
    free_agent, team_id, prone_overall, retired
)
SELECT
    player_id, first_name, last_name, date_of_birth,
    position, height, weight, bats, throws,
    free_agent,
    CASE WHEN team_id = 0 THEN 999 ELSE team_id END,
    prone_overall, retired
FROM staging.players
ON DUPLICATE KEY UPDATE
    team_id = VALUES(team_id),
    prone_overall = VALUES(prone_overall),
    retired = VALUES(retired);

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

INSERT INTO players_career_pitching_stats (
    player_id, year, team_id, game_id, league_id,
    level_id, split_id, ip, ab, tb, ha, k, bf, rs,
    bb, r, er, gb, fb, pi, ipf, g, gs, w, l, s, sa,
    da, sh, sf, ta, hra, bk, ci, iw, wp, hp, gf, dp,
    qs, svo, bs, ra, cg, sho, sb, cs, hld, ir, irs,
    wpa, li, stint, outs, sd, md, war, ra9war
)
SELECT
    s.player_id, s.year,
    CASE WHEN s.team_id=0 THEN 999 ELSE s.team_id END,
    s.game_id, s.league_id,
    s.level_id, s.split_id, s.ip, s.ab, s.tb, s.ha, s.k, s.bf, s.rs,
    s.bb, s.r, s.er, s.gb, s.fb, s.pi, s.ipf, s.g, s.gs, s.w, s.l, s.s, s.sa,
    s.da, s.sh, s.sf, s.ta, s.hra, s.bk, s.ci, s.iw, s.wp, s.hp, s.gf, s.dp,
    s.qs, s.svo, s.bs, s.ra, s.cg, s.sho, s.sb, s.cs, s.hld, s.ir, s.irs,
    s.wpa, s.li, s.stint, s.outs, s.sd, s.md, s.war, s.ra9war
FROM staging.players_career_pitching_stats s
INNER JOIN players p ON s.player_id = p.player_id
WHERE s.split_id = 1
ON DUPLICATE KEY UPDATE
    ip = VALUES(ip),
    ab = VALUES(ab),
    tb = VALUES(tb),
    ha = VALUES(ha),
    k = VALUES(k),
    bf = VALUES(bf),
    rs = VALUES(rs),
    bb = VALUES(bb),
    r = VALUES(r),
    er = VALUES(er),
    gb = VALUES(gb),
    fb = VALUES(fb),
    pi = VALUES(pi),
    ipf = VALUES(ipf),
    g = VALUES(g),
    gs = VALUES(gs),
    w = VALUES(w),
    l = VALUES(l),
    s = VALUES(s),
    sa = VALUES(sa),
    da = VALUES(da),
    sh = VALUES(sh),
    sf = VALUES(sf),
    ta = VALUES(ta),
    hra = VALUES(hra),
    bk = VALUES(bk),
    ci = VALUES(ci),
    iw = VALUES(iw),
    wp = VALUES(wp),
    hp = VALUES(hp),
    gf = VALUES(gf),
    dp = VALUES(dp),
    qs = VALUES(qs),
    svo = VALUES(svo),
    bs = VALUES(bs),
    ra = VALUES(ra),
    cg = VALUES(cg),
    sho = VALUES(sho),
    sb = VALUES(sb),
    cs = VALUES(cs),
    hld = VALUES(hld),
    ir = VALUES(ir),
    irs = VALUES(irs),
    wpa = VALUES(wpa),
    li = VALUES(li),
    stint = VALUES(stint),
    outs = VALUES(outs),
    sd = VALUES(sd),
    md = VALUES(md),
    war = VALUES(war),
    ra9war = VALUES(ra9war);
