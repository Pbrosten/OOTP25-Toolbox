-- Roster weaknesses/surpluses (ticket 0081): each of a team's batting
-- position groups, one row per (group, this team's player) pair -- name
-- included, so the widget can say *who* is thin/deep at a position, not
-- just the raw number -- plus a single all-NULL-player row for any group
-- this team has nobody rostered at, so "no player here" is still visible
-- instead of the group silently missing. Percentile reuses
-- get_org_depth_chart.sql's is_promotion_candidate formula exactly
-- (fraction of the comparison pool strictly below this player's WAR, as
-- a 0-100 percentile) -- just against a different pool (every real MLB
-- team's active roster at this group, not AAA/AA at a level) and a
-- different cutoff (50th percentile "average," not 80th
-- "promotion-worthy"). Classification itself (weakness/surplus/neutral,
-- via the 50th-percentile cutoff) happens in Python (app/api/teams.py),
-- same flat-rows-Python-aggregates split as get_org_depth_chart.sql.
--
-- Position players only (per the user, 2026-08-23): pitchers
-- (players.position = 'P') are excluded entirely, not just grouped
-- separately -- a pitching-staff weakness/surplus read isn't the same
-- shape as a lineup-spot one (roles are SP/RP/closer, not one-per-group
-- like a batting position), so it's out of scope for this widget rather
-- than force-fit into the same percentile-by-group model.
--
-- MLB (level = 1) roster only, same active/on-secondary filter as
-- get_org_depth_chart.sql/get_team_war_summary.sql -- excludes players
-- merely administratively parked under a team_id with no real roster
-- assignment.
WITH mlb_roster AS (
    SELECT p.player_id, p.team_id, p.position
    FROM players p
    JOIN teams t ON t.team_id = p.team_id
    LEFT JOIN players_service_time st ON st.player_id = p.player_id
    WHERE t.level = 1 AND t.city_id != 0
      AND p.position != 'P'
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

grouped AS (
    SELECT
        r.player_id,
        r.team_id,
        r.position AS group_code,
        -- A position player who's also a two-way player's pitching side
        -- (rare, but players_pitching_run_value is keyed off rating_id
        -- regardless of listed position) still has their pitching WAR
        -- summed in -- same two-way convention as
        -- get_org_depth_chart.sql/get_team_war_summary.sql.
        CASE
            WHEN brv.WAR IS NOT NULL AND prv.WAR IS NOT NULL THEN brv.WAR + prv.WAR
            ELSE COALESCE(brv.WAR, prv.WAR)
        END AS war
    FROM mlb_roster r
    JOIN rating rt ON rt.player_id = r.player_id
    LEFT JOIN players_run_value brv ON brv.rating_id = rt.rating_id
    LEFT JOIN players_pitching_run_value prv ON prv.rating_id = rt.rating_id
),

-- Every real MLB position player's percentile rank *and* ordinal rank
-- (ticket 0081 revision, "#N of pool_size" -- same framing as
-- get_team_war_summary.sql's team power ranking) within their own
-- group's league-wide pool (all 30 teams). Ordinal rank is 1 + the count
-- of strictly-better players -- ties share a rank, same convention as
-- get_team_war_summary.sql's RANK(), just via a correlated subquery here
-- to match this file's existing percentile-computation style rather than
-- mixing in a window function.
ranked AS (
    SELECT
        g.player_id,
        g.team_id,
        g.group_code,
        g.war,
        CASE WHEN g.war IS NULL THEN NULL ELSE ROUND(
            (
                SELECT COUNT(*) * 1.0 FROM grouped lw
                WHERE lw.group_code = g.group_code AND lw.war IS NOT NULL AND lw.war < g.war
            ) * 100 /
            (
                SELECT COUNT(*) FROM grouped lw
                WHERE lw.group_code = g.group_code AND lw.war IS NOT NULL
            )
        ) END AS league_percentile,
        CASE WHEN g.war IS NULL THEN NULL ELSE (
            SELECT COUNT(*) + 1 FROM grouped lw
            WHERE lw.group_code = g.group_code AND lw.war IS NOT NULL AND lw.war > g.war
        ) END AS league_rank
    FROM grouped g
)

SELECT
    all_groups.group_code,
    r.player_id,
    pl.first_name,
    pl.last_name,
    r.war,
    r.league_percentile,
    r.league_rank,
    -- Pool size doesn't depend on this team's player at all (it's the
    -- same for every row in a group) -- computed off all_groups/`grouped`
    -- directly rather than through `r` so it's still populated on the
    -- all-NULL-player placeholder row for a group this team has nobody
    -- rostered at.
    (
        SELECT COUNT(*) FROM grouped lw
        WHERE lw.group_code = all_groups.group_code AND lw.war IS NOT NULL
    ) AS league_pool_size
FROM (SELECT DISTINCT group_code FROM grouped) all_groups
LEFT JOIN ranked r
  ON r.group_code = all_groups.group_code AND r.team_id = %(team_id)s
LEFT JOIN players pl ON pl.player_id = r.player_id
ORDER BY all_groups.group_code, r.war DESC;
