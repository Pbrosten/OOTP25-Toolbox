-- Prospect-eligible player list (ticket 0069). "Prospect" per ticket 0043's
-- Design choices: currently on a non-MLB affiliate (teams.level != 1), or a
-- just-debuted MLB rookie with zero recorded MLB service
-- (players_service_time.mlb_service_years = 0). level = 5 (exhibition
-- "All-Star" teams, ticket 0062) and team_id = 999 (Free Agents) are
-- excluded -- not real affiliates, same convention as get_org_depth_chart.sql.
--
-- Post-close correction (user report): the level/service-time definition
-- alone let a veteran journeyman sent back down to AAA (e.g. a 32-year-old
-- reliever) show up as a "prospect" -- age < 26 added as an additional
-- gate, on top of (not instead of) the level/service-time check above, so
-- a rostered MLB regular briefly optioned down still isn't miscategorized.
--
-- Returns one row per prospect's latest rating, with every raw column
-- ticket 0068's calc module needs to build both a talent-ceiling and a
-- current-form projection input. Both batting-side and pitching-side
-- columns are always selected (LEFT JOINed); the caller
-- (app/api/prospects.py) picks the side that matches players.position, the
-- same explicit-position-gate convention get_player_rating_trends.sql uses
-- rather than relying on which side happens to have rows.
--
-- team_id/position/level/player_id are optional filters (NULL = no filter
-- on that dimension). team_id scopes to a single org: the given MLB team
-- itself plus every affiliate whose parent_team_id points at it, same
-- org-scoping as get_org_depth_chart.sql -- not restricted to a level-1
-- team_id here since a caller may also want to scope to a single affiliate
-- team directly. player_id (ticket 0071) scopes to a single player -- used
-- by GET /api/prospects/<player_id> to answer "is this specific player a
-- prospect" without pulling an org's whole list, reusing this same query
-- rather than a parallel single-player one.
--
-- level = 0 (ticket 0073 post-close correction, user report -- Cris
-- Ortega): a player parked at a real level-1 team_id with no real MLB (or
-- even minor-league) roster assignment -- confirmed real case, a
-- 17-year-old international-complex signee whose org has no actual
-- "International Complex" team to assign him to in this save (same root
-- cause get_org_depth_chart.sql's is_active/is_on_secondary check already
-- excludes from the level-1 roster, ticket 0064's post-close correction).
-- The Prospect Pipeline's job is different from the depth chart's --
-- these players should stay listed as prospects, not be silently dropped,
-- but shouldn't be mislabeled "MLB" -- so instead of excluding them, their
-- *displayed* level is overridden to a synthetic 0 ("Int'l Complex" in the
-- frontend), never a real teams.level value (confirmed: teams.level only
-- ever holds NULL/1/2/3/4/5/6 in this save). The level *filter* below
-- applies to this same overridden value (via the outer prospects CTE, not
-- prospect_candidates), so ?level=0 actually finds these players too.
WITH prospect_candidates AS (
    SELECT
        p.player_id, p.first_name, p.last_name, p.position, p.bats,
        p.birth_date, p.age, p.prone_overall, p.team_id,
        CASE
            WHEN t.level = 1
                 AND COALESCE(st.is_active, 0) = 0
                 AND COALESCE(st.is_on_secondary, 0) = 0
            THEN 0
            ELSE t.level
        END AS level,
        t.abbr AS team_abbr, t.parent_team_id,
        st.mlb_service_years
    FROM players p
    JOIN teams t ON t.team_id = p.team_id
    LEFT JOIN players_service_time st ON st.player_id = p.player_id
    WHERE p.retired = 0
      AND t.team_id != 999
      AND t.level != 5
      AND p.age < 26
      AND (
          t.level != 1
          OR COALESCE(st.mlb_service_years, 0) = 0
      )
      AND (%(team_id)s IS NULL OR p.team_id = %(team_id)s OR t.parent_team_id = %(team_id)s)
      AND (%(position)s IS NULL OR p.position = %(position)s)
      AND (%(player_id)s IS NULL OR p.player_id = %(player_id)s)
),
prospects AS (
    SELECT * FROM prospect_candidates
    WHERE %(level)s IS NULL OR level = %(level)s
),
latest_rating AS (
    SELECT pr.player_id, MAX(pr.rating_date) AS rating_date
    FROM players_rating pr
    JOIN prospects pl ON pl.player_id = pr.player_id
    GROUP BY pr.player_id
),
rating AS (
    SELECT pr.rating_id, pr.player_id, pr.rating_date
    FROM players_rating pr
    JOIN latest_rating lr
      ON lr.player_id = pr.player_id AND lr.rating_date = pr.rating_date
)
SELECT
    pl.player_id, pl.first_name, pl.last_name, pl.position, pl.bats,
    pl.birth_date, pl.age, pl.prone_overall, pl.team_id, pl.team_abbr,
    pl.level, pl.parent_team_id, pl.mlb_service_years,
    r.rating_id, r.rating_date,

    b.babip AS bat_babip, b.gap AS bat_gap, b.eye AS bat_eye,
    b.power AS bat_power, b.strikeouts AS bat_strikeouts,
    bt.babip AS bat_babip_talent, bt.gap AS bat_gap_talent,
    bt.eye AS bat_eye_talent, bt.power AS bat_power_talent,
    bt.strikeouts AS bat_strikeouts_talent,

    bp.speed, bp.steal, bp.baserunning,

    fp.pos2, fp.pos3, fp.pos4, fp.pos5, fp.pos6, fp.pos7, fp.pos8, fp.pos9,
    fpt.pos2 AS pos2_talent, fpt.pos3 AS pos3_talent, fpt.pos4 AS pos4_talent,
    fpt.pos5 AS pos5_talent, fpt.pos6 AS pos6_talent, fpt.pos7 AS pos7_talent,
    fpt.pos8 AS pos8_talent, fpt.pos9 AS pos9_talent,

    pp.role AS pitch_role, pp.stuff AS pitch_stuff, pp.control AS pitch_control,
    pp.pbabip AS pitch_pbabip, pp.hra AS pitch_hra, pp.stamina AS pitch_stamina,
    pp.hold AS pitch_hold,
    ppt.stuff AS pitch_stuff_talent, ppt.control AS pitch_control_talent,
    ppt.pbabip AS pitch_pbabip_talent, ppt.hra AS pitch_hra_talent
FROM prospects pl
JOIN rating r ON r.player_id = pl.player_id
LEFT JOIN players_batting b ON b.rating_id = r.rating_id
LEFT JOIN players_batting_talent bt ON bt.rating_id = r.rating_id
LEFT JOIN players_basepath bp ON bp.rating_id = r.rating_id
LEFT JOIN players_fielding_position fp ON fp.rating_id = r.rating_id
LEFT JOIN players_fielding_position_talent fpt ON fpt.rating_id = r.rating_id
LEFT JOIN players_pitching pp ON pp.rating_id = r.rating_id
LEFT JOIN players_pitching_talent ppt ON ppt.rating_id = r.rating_id;
