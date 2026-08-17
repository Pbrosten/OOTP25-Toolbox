-- Ticket 0066: bulk equivalent of app/db/sql_scripts/api/
-- get_player_contract_inputs.sql -- one row per player with an actual
-- signed contract (years > 0 -- the years=0/current_year=0 row OOTP
-- writes for every unsigned player is excluded here, not just filtered
-- by the caller), used to re-derive contract_value.py's WAR_DOLLAR_VALUE/
-- RECOMMENDATION_EXTEND_THRESHOLD from real players_contract data (see
-- app/db/update.py::compute_market_constants). Latest rating per player
-- via ROW_NUMBER() -- unlike the single-player version, this can't just
-- ORDER BY rating_date DESC LIMIT 1 across many players at once.
WITH latest_rating AS (
    SELECT
        pr.player_id, pr.rating_id,
        ROW_NUMBER() OVER (PARTITION BY pr.player_id ORDER BY pr.rating_date DESC) AS rn
    FROM players_rating pr
)
SELECT
    p.player_id, p.age, p.prone_overall,
    bwr.WAR AS batting_war,
    pwr.WAR AS pitching_war,
    pp.role AS pitching_role,
    st.mlb_service_years,
    c.current_year, c.years,
    c.salary0, c.salary1, c.salary2, c.salary3, c.salary4,
    c.salary5, c.salary6, c.salary7, c.salary8, c.salary9,
    c.salary10, c.salary11, c.salary12, c.salary13, c.salary14
FROM players p
JOIN players_contract c ON c.player_id = p.player_id AND c.years > 0
LEFT JOIN latest_rating lr ON lr.player_id = p.player_id AND lr.rn = 1
LEFT JOIN players_run_value bwr ON bwr.rating_id = lr.rating_id
LEFT JOIN players_pitching_run_value pwr ON pwr.rating_id = lr.rating_id
LEFT JOIN players_pitching pp ON pp.rating_id = lr.rating_id
LEFT JOIN players_service_time st ON st.player_id = p.player_id;
