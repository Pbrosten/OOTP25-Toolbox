-- Ticket 0066: pooled real batting totals over the 3 most recently-ingested
-- distinct years for league_id = 203 (MLB), used to recompute this save's
-- own lg_woba (see app/db/projection.py::compute_league_baselines). PA >=
-- 50 excludes token cameo season-lines (a September call-up's 4-PA line
-- shouldn't be pooled at equal row-weight to a full-season regular).
WITH recent_years AS (
    SELECT DISTINCT year
    FROM players_career_batting_stats
    WHERE league_id = 203
    ORDER BY year DESC
    LIMIT 3
)
SELECT
    MIN(s.year) AS window_start_year,
    MAX(s.year) AS window_end_year,
    SUM(s.pa) AS pa,
    SUM(s.bb) AS bb,
    SUM(s.hp) AS hp,
    SUM(s.h) AS h,
    SUM(s.d) AS d,
    SUM(s.t) AS t,
    SUM(s.hr) AS hr
FROM players_career_batting_stats s
JOIN recent_years ry ON s.year = ry.year
WHERE s.league_id = 203 AND s.pa >= 50;
