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
    league_id, human_team, background_color, text_color,
    parent_team_id, level
)
SELECT
    team_id, name, abbr, nickname, division_id,
    league_id, human_team, background_color_id, text_color_id,
    parent_team_id, level
FROM staging.teams
ON DUPLICATE KEY UPDATE
    name = VALUES(name),
    abbr = VALUES(abbr),
    nickname = VALUES(nickname),
    division_id = VALUES(division_id),
    league_id = VALUES(league_id),
    human_team = VALUES(human_team),
    background_color = VALUES(background_color),
    text_color = VALUES(text_color),
    parent_team_id = VALUES(parent_team_id),
    level = VALUES(level);

-- Excludes players who are both retired and inactive since before 2024 --
-- ootp.players carries a save's entire player history otherwise (see
-- ticket 0046), most of which is irrelevant to current-day GM
-- decision-making. "Active" is judged from staging's raw career stats
-- (not ootp's, since this filter has to decide inclusion before those
-- rows exist in ootp) rather than a single year/debut field, because
-- staging.players has no such field (confirmed against a real dump
-- export). retired=0 players are always kept regardless of recent stat
-- history -- e.g. a not-yet-debuted prospect has zero career-stat rows
-- but is very much in scope, and an unsigned-but-not-retired free agent
-- who last played a year or two ago may still be a live asset.
--
-- Materialized into an indexed temp table rather than inlined as
-- correlated EXISTS subqueries against staging.players_career_batting_stats/
-- _pitching_stats directly in the INSERT...SELECT below. Those staging
-- tables are freshly loaded raw dump copies with zero indexes
-- (confirmed -- SHOW INDEX returns nothing) at real-save scale (670k+/
-- 370k+ rows), and against a real dump this app's own transaction settings
-- (autocommit=0, REPEATABLE READ -- see connection.py) made InnoDB take a
-- shared lock on every row scanned while evaluating the correlated
-- subqueries inline (over 1,000,000 row locks observed, "Sending data" for
-- 5+ minutes on a single heap). Precomputing the small (~15k-row) active-id
-- set here, once, keeps the actual players INSERT's WHERE clause an
-- indexed membership check instead -- same real dump went from not
-- completing in 5 minutes to well under a second.
DROP TEMPORARY TABLE IF EXISTS recently_active_player_ids;
CREATE TEMPORARY TABLE recently_active_player_ids (
    player_id INT PRIMARY KEY
);
INSERT INTO recently_active_player_ids
SELECT player_id FROM staging.players_career_batting_stats WHERE year >= 2024
UNION
SELECT player_id FROM staging.players_career_pitching_stats WHERE year >= 2024;

INSERT INTO players (
    player_id, first_name, last_name, birth_date,
    position, height, weight, bats, throws,
    free_agent, team_id, prone_overall, retired
)
SELECT
    s.player_id, s.first_name, s.last_name, s.date_of_birth,
    s.position, s.height, s.weight, s.bats, s.throws,
    s.free_agent,
    CASE WHEN s.team_id = 0 THEN 999 ELSE s.team_id END,
    s.prone_overall, s.retired
FROM staging.players s
WHERE s.retired = 0
   OR s.player_id IN (SELECT player_id FROM recently_active_player_ids)
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

-- Contract / salary / service-time: see ticket 0054. Current-state upserts,
-- not dated snapshots -- these staging tables only ever appear in yearly
-- heaps (confirmed against a real dump export), matching players/teams'
-- own upsert cadence above rather than players_rating's append-only one.
INSERT INTO players_contract (
    player_id, team_id, season_year, years, current_year,
    salary0, salary1, salary2, salary3, salary4,
    salary5, salary6, salary7, salary8, salary9,
    salary10, salary11, salary12, salary13, salary14,
    no_trade, last_year_team_option, last_year_player_option,
    last_year_vesting_option, opt_out
)
SELECT
    s.player_id, s.team_id, s.season_year, s.years, s.current_year,
    s.salary0, s.salary1, s.salary2, s.salary3, s.salary4,
    s.salary5, s.salary6, s.salary7, s.salary8, s.salary9,
    s.salary10, s.salary11, s.salary12, s.salary13, s.salary14,
    s.no_trade, s.last_year_team_option, s.last_year_player_option,
    s.last_year_vesting_option, s.opt_out
FROM staging.players_contract s
INNER JOIN players p ON s.player_id = p.player_id
ON DUPLICATE KEY UPDATE
    team_id = VALUES(team_id), season_year = VALUES(season_year),
    years = VALUES(years), current_year = VALUES(current_year),
    salary0 = VALUES(salary0), salary1 = VALUES(salary1),
    salary2 = VALUES(salary2), salary3 = VALUES(salary3),
    salary4 = VALUES(salary4), salary5 = VALUES(salary5),
    salary6 = VALUES(salary6), salary7 = VALUES(salary7),
    salary8 = VALUES(salary8), salary9 = VALUES(salary9),
    salary10 = VALUES(salary10), salary11 = VALUES(salary11),
    salary12 = VALUES(salary12), salary13 = VALUES(salary13),
    salary14 = VALUES(salary14), no_trade = VALUES(no_trade),
    last_year_team_option = VALUES(last_year_team_option),
    last_year_player_option = VALUES(last_year_player_option),
    last_year_vesting_option = VALUES(last_year_vesting_option),
    opt_out = VALUES(opt_out);

-- Placeholder year=0/salary=0 rows (present for most players) are excluded
-- -- see ticket 0054's Design choices. Append-only ledger, like
-- players_rating, so INSERT IGNORE rather than an upsert.
INSERT IGNORE INTO players_salary_history (player_id, team_id, year, salary)
SELECT s.player_id, s.team_id, s.year, s.salary
FROM staging.players_salary_history s
INNER JOIN players p ON s.player_id = p.player_id
WHERE s.year != 0;

INSERT INTO players_service_time (
    player_id, mlb_service_years, mlb_service_days,
    pro_service_years, has_received_arbitration
)
SELECT
    s.player_id, s.mlb_service_years, s.mlb_service_days,
    s.pro_service_years, s.has_received_arbitration
FROM staging.players_roster_status s
INNER JOIN players p ON s.player_id = p.player_id
ON DUPLICATE KEY UPDATE
    mlb_service_years = VALUES(mlb_service_years),
    mlb_service_days = VALUES(mlb_service_days),
    pro_service_years = VALUES(pro_service_years),
    has_received_arbitration = VALUES(has_received_arbitration);
