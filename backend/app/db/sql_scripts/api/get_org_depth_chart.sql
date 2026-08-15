-- Org depth chart (ticket 0063): every player on the given MLB team's
-- roster plus its AAA/AA/A/Rookie affiliates (teams.parent_team_id,
-- ticket 0062), one row per player with their level, primary position,
-- pitching role group (SP/RP, NULL for position players), and current
-- projected WAR. Shaping into {level: {group: [players]}} happens in
-- Python (app/api/teams.py), not here -- mirrors get_player_contract_
-- inputs.sql staying a flat row-returning query.
WITH org_teams AS (
    SELECT team_id, level FROM teams WHERE team_id = %(team_id)s
    UNION
    -- level = 5 is a save-specific anomaly (exhibition "All-Star" teams,
    -- confirmed in ticket 0062's investigation), not a real affiliate --
    -- excluded here the same way team_id = 999 (Free Agents) already is
    -- via the FK relationship (Free Agents has no real players.team_id
    -- pointing at 999 for active players anyway).
    SELECT team_id, level FROM teams WHERE parent_team_id = %(team_id)s AND level != 5
),

roster AS (
    SELECT p.player_id, p.first_name, p.last_name, p.team_id, p.position,
           ot.level
    FROM players p
    JOIN org_teams ot ON ot.team_id = p.team_id
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
)

SELECT
    r.player_id,
    r.first_name,
    r.last_name,
    r.team_id,
    r.level,
    r.position,
    CASE pp.role
        WHEN 11 THEN 'SP'
        WHEN 12 THEN 'RP'
        WHEN 13 THEN 'RP'
        ELSE NULL
    END AS role_group,
    -- Two-way players (both batting and pitching WAR present) get NULL,
    -- not a netted/summed figure -- same "never net batting/pitching WAR"
    -- precedent as ticket 0056's surplus-value calculation.
    CASE
        WHEN brv.WAR IS NOT NULL AND prv.WAR IS NOT NULL THEN NULL
        ELSE COALESCE(brv.WAR, prv.WAR)
    END AS war
FROM roster r
JOIN rating rt ON rt.player_id = r.player_id
LEFT JOIN players_run_value brv ON brv.rating_id = rt.rating_id
LEFT JOIN players_pitching_run_value prv ON prv.rating_id = rt.rating_id
LEFT JOIN players_pitching pp ON pp.rating_id = rt.rating_id;
