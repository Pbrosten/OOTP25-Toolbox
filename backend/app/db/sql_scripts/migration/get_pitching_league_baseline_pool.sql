-- Ticket 0066: pooled real pitching totals over the 3 most recently-
-- ingested distinct years for league_id = 203 (MLB), used to recompute
-- this save's own lg_pwoba/ra9_baseline (see app/db/projection.py::
-- compute_league_baselines). outs >= 60 (20 IP) excludes token cameo
-- season-lines, same reasoning as the batting pool's PA floor. outs (a
-- true out count) is summed for the innings conversion instead of the ip
-- column, which OOTP stores in baseball notation (6.1 = 6 and 1/3 innings,
-- not a real decimal) and so isn't safely summable across rows.
WITH recent_years AS (
    SELECT DISTINCT year
    FROM players_career_pitching_stats
    WHERE league_id = 203
    ORDER BY year DESC
    LIMIT 3
)
SELECT
    MIN(s.year) AS window_start_year,
    MAX(s.year) AS window_end_year,
    SUM(s.bf) AS bf,
    SUM(s.bb) AS bb,
    SUM(s.hp) AS hp,
    SUM(s.ha) AS ha,
    SUM(s.hra) AS hra,
    SUM(s.ra) AS ra,
    SUM(s.outs) AS outs
FROM players_career_pitching_stats s
JOIN recent_years ry ON s.year = ry.year
WHERE s.league_id = 203 AND s.outs >= 60;
