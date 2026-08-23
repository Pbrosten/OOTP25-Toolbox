-- Team WAR summary + power ranking (ticket 0079, revised to add ranking):
-- a team's aggregate current-roster WAR, plus its rank among all real MLB
-- teams by that same figure, for the GM Command Center dashboard's
-- headline stat (ticket 0038). Sums each roster player's current-rating
-- batting WAR (players_run_value) and pitching WAR
-- (players_pitching_run_value) at their latest rating snapshot -- same
-- two-way-sums-both convention as get_org_depth_chart.sql (ticket 0063),
-- and the same MLB active-roster filter (players_service_time.is_active/
-- is_on_secondary, ticket 0064 post-close correction) that excludes
-- players merely administratively parked under a team_id with no real
-- roster assignment.
--
-- Ranking needs every real MLB team's total in the same query (not just
-- the requested team's), including a team with zero rated roster players
-- (war = 0, not missing) -- mlb_teams/team_war below build that full
-- league table via LEFT JOINs before ranking, rather than only ranking
-- among teams that happened to already have a row.
WITH mlb_teams AS (
    -- city_id != 0 excludes the save's exhibition teams also tagged
    -- level = 1 (AL/NL All-Stars/Future Stars) -- same exclusion as
    -- get_mlb_teams/get_team_depth_chart.
    SELECT team_id FROM teams WHERE level = 1 AND city_id != 0
),

roster AS (
    SELECT p.player_id, p.team_id
    FROM players p
    JOIN mlb_teams mt ON mt.team_id = p.team_id
    LEFT JOIN players_service_time st ON st.player_id = p.player_id
    WHERE st.is_active = 1 OR st.is_on_secondary = 1
),

latest_rating AS (
    SELECT pr.player_id, MAX(pr.rating_date) AS rating_date
    FROM players_rating pr
    JOIN roster r ON r.player_id = pr.player_id
    GROUP BY pr.player_id
),

rating AS (
    SELECT pr.rating_id, pr.player_id
    FROM players_rating pr
    JOIN latest_rating lr
      ON lr.player_id = pr.player_id AND lr.rating_date = pr.rating_date
),

player_war AS (
    SELECT
        r.team_id,
        CASE
            WHEN brv.WAR IS NOT NULL AND prv.WAR IS NOT NULL THEN brv.WAR + prv.WAR
            ELSE COALESCE(brv.WAR, prv.WAR)
        END AS war
    FROM roster r
    JOIN rating rt ON rt.player_id = r.player_id
    LEFT JOIN players_run_value brv ON brv.rating_id = rt.rating_id
    LEFT JOIN players_pitching_run_value prv ON prv.rating_id = rt.rating_id
),

team_war AS (
    SELECT mt.team_id, COALESCE(SUM(pw.war), 0) AS war
    FROM mlb_teams mt
    LEFT JOIN player_war pw ON pw.team_id = mt.team_id
    GROUP BY mt.team_id
),

ranked AS (
    SELECT
        team_id,
        war,
        -- RANK() (not ROW_NUMBER()) so teams tied on WAR share the same
        -- rank, per the standard "power ranking" convention.
        RANK() OVER (ORDER BY war DESC) AS team_rank
    FROM team_war
)

SELECT
    team_id,
    war,
    team_rank,
    (SELECT COUNT(*) FROM mlb_teams) AS total_teams
FROM ranked
WHERE team_id = %(team_id)s;
