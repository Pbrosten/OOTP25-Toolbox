-- League-wide prospect leaderboard (ticket 0076): reads ticket 0075's
-- persisted players_prospect_value table -- no runtime BatterProjection/
-- PitcherProjection calls at all, unlike get_prospects.sql's live-compute
-- path (0069). Same prospect-definition filter as get_prospects.sql,
-- including its level=0 ("Int'l Complex", ticket 0073) override and the
-- two-CTE split that lets ?level=0 filter on the overridden value rather
-- than the raw teams.level -- re-validated against CURRENT players/teams
-- state, not from anything stored per-heap (players_prospect_value has no
-- level-dependent columns -- see ticket 0075's Design choices).
--
-- team_id/position/level are optional filters, same meaning as
-- get_prospects.sql's (no player_id here -- this query is always a list).
--
-- Returns the FULL ranked candidate set (fv DESC, surplus_value DESC as
-- tiebreak) that actually has a persisted value -- INNER JOINed to
-- players_prospect_value, so a prospect with no persisted row (missing
-- rating data, or a heap processed before ticket 0075 existed -- see
-- 0075's Cris Ortega finding) is simply absent from the leaderboard
-- rather than shown as unavailable, unlike get_prospects.sql's live path.
-- app/api/prospects.py's leaderboard branch does the top_overall
-- pagination and top_by_position/top_by_level grouping in Python from
-- this one query -- the global sort order already makes "first N seen
-- for group X" equal "top N for group X," so no separate queries needed.
WITH prospect_candidates AS (
    SELECT
        p.player_id, p.first_name, p.last_name, p.position, p.age,
        p.team_id,
        CASE
            WHEN t.level = 1
                 AND COALESCE(st.is_active, 0) = 0
                 AND COALESCE(st.is_on_secondary, 0) = 0
            THEN 0
            ELSE t.level
        END AS level,
        t.abbr AS team_abbr, t.parent_team_id,
        -- org_abbr (user request): the parent MLB organization's
        -- abbreviation, not the player's own immediate affiliate team --
        -- a level-1 team's own parent_team_id is always 0 (confirmed
        -- against real data, never NULL), meaning "no parent, this team
        -- IS the org," so org_team's own team_id is used in that case.
        org_t.abbr AS org_abbr,
        st.mlb_service_years
    FROM players p
    JOIN teams t ON t.team_id = p.team_id
    JOIN teams org_t ON org_t.team_id = IF(t.parent_team_id = 0, t.team_id, t.parent_team_id)
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
    SELECT pr.rating_id, pr.player_id
    FROM players_rating pr
    JOIN latest_rating lr
      ON lr.player_id = pr.player_id AND lr.rating_date = pr.rating_date
)
SELECT
    pl.player_id, pl.first_name, pl.last_name, pl.position, pl.age,
    pl.team_id, pl.team_abbr, pl.org_abbr, pl.level, pl.parent_team_id,
    pl.mlb_service_years,
    pv.fv, pv.surplus_value, pv.expected_war, pv.star_odds, pv.current_fv, pv.risk_tag
FROM prospects pl
JOIN rating r ON r.player_id = pl.player_id
JOIN players_prospect_value pv ON pv.rating_id = r.rating_id
ORDER BY pv.fv DESC, pv.surplus_value DESC;
