-- Over/underperformers (ticket 0080): a team's active MLB roster
-- players' real current-season actual WAR
-- (players_career_batting_stats/players_career_pitching_stats) minus
-- their latest projected WAR (players_run_value/
-- players_pitching_run_value) -- one row per qualifying roster player,
-- delta = actual - projected. Notable-delta classification (what counts
-- as a "notable" over/underperformance) happens in Python
-- (app/api/teams.py), same flat-rows-Python-classifies split as
-- get_team_roster_strength.sql/get_team_contract_inputs.sql.
--
-- "Current season" (Design choices, ticket 0080): the single most
-- recent year recorded across the whole save (GREATEST of both career
-- tables' own MAX(year) -- normally in lockstep, but this is defensive
-- against one table lagging), not each player's own last-recorded year
-- -- a player who debuted in an earlier season and hasn't played *this*
-- one yet has no real "current-season actual" to compare, and should be
-- excluded outright rather than silently compared against a stale year
-- or zero-filled (a real bug caught while building this query: a never-
-- yet-debuted player defaulted to actual_war=0 read as "underperforming"
-- his positive projection, when he simply hasn't played yet).
--
-- Qualifying sample floor (PA >= 50 batting, outs >= 60 pitching -- ~20
-- IP; outs, not the ip column, since OOTP stores ip in baseball notation
-- (6.1 = 6 1/3 innings) which isn't safely summable across rows): the
-- exact same "exclude token cameo season-lines" thresholds already used
-- by get_batting_league_baseline_pool.sql/
-- get_pitching_league_baseline_pool.sql (ticket 0066) -- without this, a
-- player with a handful of PA (e.g. a September call-up) can show a huge
-- meaningless delta purely from small-sample noise.
--
-- MLB (level = 1) roster only, same active/on-secondary filter as
-- get_org_depth_chart.sql/get_team_war_summary.sql/
-- get_team_roster_strength.sql/get_team_contract_inputs.sql.
WITH mlb_roster AS (
    SELECT p.player_id, p.first_name, p.last_name
    FROM players p
    JOIN teams t ON t.team_id = p.team_id
    LEFT JOIN players_service_time st ON st.player_id = p.player_id
    WHERE t.level = 1 AND t.city_id != 0
      AND p.team_id = %(team_id)s
      AND (st.is_active = 1 OR st.is_on_secondary = 1)
),

latest_rating AS (
    SELECT pr.player_id, MAX(pr.rating_date) AS rating_date
    FROM players_rating pr
    JOIN mlb_roster r ON r.player_id = pr.player_id
    GROUP BY pr.player_id
),

rating AS (
    SELECT pr.rating_id, pr.player_id
    FROM players_rating pr
    JOIN latest_rating lr
      ON lr.player_id = pr.player_id AND lr.rating_date = pr.rating_date
),

projected AS (
    SELECT
        r.player_id,
        CASE
            WHEN brv.WAR IS NOT NULL AND prv.WAR IS NOT NULL THEN brv.WAR + prv.WAR
            ELSE COALESCE(brv.WAR, prv.WAR)
        END AS projected_war
    FROM rating r
    LEFT JOIN players_run_value brv ON brv.rating_id = r.rating_id
    LEFT JOIN players_pitching_run_value prv ON prv.rating_id = r.rating_id
),

current_year AS (
    SELECT GREATEST(
        (SELECT MAX(year) FROM players_career_batting_stats),
        (SELECT MAX(year) FROM players_career_pitching_stats)
    ) AS yr
),

actual_batting AS (
    SELECT cb.player_id, SUM(cb.war) AS war
    FROM players_career_batting_stats cb
    JOIN current_year cy ON cb.year = cy.yr
    WHERE cb.split_id = 1 AND cb.league_id = 203
    GROUP BY cb.player_id
    HAVING SUM(cb.pa) >= 50
),

actual_pitching AS (
    SELECT cp.player_id, SUM(cp.war) AS war
    FROM players_career_pitching_stats cp
    JOIN current_year cy ON cp.year = cy.yr
    WHERE cp.split_id = 1 AND cp.league_id = 203
    GROUP BY cp.player_id
    HAVING SUM(cp.outs) >= 60
)

SELECT
    m.player_id,
    m.first_name,
    m.last_name,
    ab.war AS actual_batting_war,
    ap.war AS actual_pitching_war,
    p.projected_war,
    (COALESCE(ab.war, 0) + COALESCE(ap.war, 0)) - COALESCE(p.projected_war, 0) AS delta
FROM mlb_roster m
LEFT JOIN actual_batting ab ON ab.player_id = m.player_id
LEFT JOIN actual_pitching ap ON ap.player_id = m.player_id
LEFT JOIN projected p ON p.player_id = m.player_id
-- A player with neither a qualifying batting nor pitching sample this
-- season has nothing to compare (see "current season" note above) --
-- excluded here rather than returned with a fabricated zero actual.
WHERE ab.player_id IS NOT NULL OR ap.player_id IS NOT NULL
ORDER BY delta DESC;
