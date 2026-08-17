-- Inputs for surplus-value calculation (ticket 0056): latest heap's
-- batting/pitching WAR (both present => two-way, caller skips), current
-- age, service time, and signed-contract salary schedule if any. LEFT
-- JOINs throughout so a player missing any of these (no contract, no
-- service-time row, no ratings at all) still returns one row with NULLs
-- rather than no row -- the caller treats missing pieces as "not available",
-- not a 404.
-- prone_overall (injury-risk proxy) and pitching role are added for ticket
-- 0059's injury-discount multiplier lookup -- role comes from the same
-- latest-heap players_pitching row as pitching_war, via rating_id.
--
-- war_dollar_value/recommendation_extend_threshold (ticket 0066): this
-- save's own recalibrated contract_value.py constants
-- (compute_market_constants(), recomputed once per long heap) -- LEFT
-- JOIN, not CROSS JOIN, so a not-yet-computed baseline (before the first
-- long heap) leaves both NULL instead of dropping the row --
-- calculate_surplus_value()/recommend_contract_action() fall back to
-- their hardcoded module constants when NULL.
SELECT
    p.age,
    p.prone_overall,
    bwr.WAR AS batting_war,
    pwr.WAR AS pitching_war,
    pp.role AS pitching_role,
    st.mlb_service_years,
    c.current_year,
    c.years,
    c.salary0, c.salary1, c.salary2, c.salary3, c.salary4,
    c.salary5, c.salary6, c.salary7, c.salary8, c.salary9,
    c.salary10, c.salary11, c.salary12, c.salary13, c.salary14,
    mb.war_dollar_value, mb.recommendation_extend_threshold
FROM players p
LEFT JOIN players_rating pr ON pr.player_id = p.player_id
LEFT JOIN players_run_value bwr ON bwr.rating_id = pr.rating_id
LEFT JOIN players_pitching_run_value pwr ON pwr.rating_id = pr.rating_id
LEFT JOIN players_pitching pp ON pp.rating_id = pr.rating_id
LEFT JOIN players_service_time st ON st.player_id = p.player_id
LEFT JOIN players_contract c ON c.player_id = p.player_id
LEFT JOIN (
    SELECT war_dollar_value, recommendation_extend_threshold
    FROM market_baselines ORDER BY id DESC LIMIT 1
) AS mb ON TRUE
WHERE p.player_id = %(player_id)s
ORDER BY pr.rating_date DESC
LIMIT 1;
