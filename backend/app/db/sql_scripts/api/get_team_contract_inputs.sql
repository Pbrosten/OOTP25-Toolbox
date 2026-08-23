-- Contract/arbitration decision inputs, team-scoped (ticket 0082): same
-- per-player shape as get_player_contract_inputs.sql (ticket 0056), just
-- for every player on a team's current MLB roster in one query instead
-- of one row at a time -- avoids an N+1 fetch loop from the dashboard
-- widget. Same LEFT JOINs throughout, same reasoning: a player missing
-- any of these (no contract, no service-time row) still returns one row
-- with NULLs rather than no row --
-- app/player_projection/contract_value.py's
-- compute_surplus_value_and_recommendation() treats missing pieces as
-- "not available," not a 404 equivalent.
--
-- MLB (level = 1) roster only, same active/on-secondary filter as
-- get_org_depth_chart.sql/get_team_war_summary.sql/
-- get_team_roster_strength.sql -- excludes players merely
-- administratively parked under the team_id with no real roster
-- assignment. Unlike 0081's roster-strength widget, pitchers ARE
-- included here -- contract/arbitration decisions apply to the whole
-- roster, not just lineup spots.
WITH mlb_roster AS (
    SELECT p.player_id, p.first_name, p.last_name, p.age, p.prone_overall,
           st.mlb_service_years
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
)

SELECT
    r.player_id,
    r.first_name,
    r.last_name,
    r.age,
    r.prone_overall,
    bwr.WAR AS batting_war,
    pwr.WAR AS pitching_war,
    pp.role AS pitching_role,
    r.mlb_service_years,
    c.current_year,
    c.years,
    c.salary0, c.salary1, c.salary2, c.salary3, c.salary4,
    c.salary5, c.salary6, c.salary7, c.salary8, c.salary9,
    c.salary10, c.salary11, c.salary12, c.salary13, c.salary14,
    mb.war_dollar_value, mb.recommendation_extend_threshold
FROM mlb_roster r
JOIN rating rt ON rt.player_id = r.player_id
LEFT JOIN players_run_value bwr ON bwr.rating_id = rt.rating_id
LEFT JOIN players_pitching_run_value pwr ON pwr.rating_id = rt.rating_id
LEFT JOIN players_pitching pp ON pp.rating_id = rt.rating_id
LEFT JOIN players_contract c ON c.player_id = r.player_id
LEFT JOIN (
    SELECT war_dollar_value, recommendation_extend_threshold
    FROM market_baselines ORDER BY id DESC LIMIT 1
) AS mb ON TRUE;
