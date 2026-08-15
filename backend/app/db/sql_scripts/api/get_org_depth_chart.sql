-- Org depth chart (ticket 0063): every player on the given MLB team's
-- roster plus its AAA/AA/A/Rookie affiliates (teams.parent_team_id,
-- ticket 0062), one row per player with their level, primary position,
-- pitching role group (SP/RP, NULL for position players), and current
-- projected WAR. Shaping into {level: {group: [players]}} happens in
-- Python (app/api/teams.py), not here -- mirrors get_player_contract_
-- inputs.sql staying a flat row-returning query. Excludes players merely
-- administratively parked under the MLB team_id with no real roster
-- assignment (players_service_time.is_active/is_on_secondary, ticket
-- 0064 post-close correction) -- see the roster CTE below.
--
-- is_promotion_candidate (ticket 0064): WAR is computed from current
-- ratings evaluated as if the player were already in MLB (see
-- app/player_projection/batter.py/pitcher.py -- no level/league
-- adjustment anywhere), so it's only a meaningful ranking signal at
-- levels close to MLB-readiness. Scoped to AAA/AA (level IN (2, 3)) only
-- -- flags a player whose WAR is in the top fifth (80th percentile or
-- higher) of every player at that *same level across the whole league*
-- (not just this org), per the user's explicit rule. A/Rookie (4, 6)
-- don't get individual WAR-ranked lists at all (see app/api/teams.py),
-- so this doesn't apply there.
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
    -- t.abbr (ticket 0064): a level can hold multiple affiliate teams
    -- (e.g. two A-level affiliates), so team_id alone doesn't let the
    -- frontend distinguish which affiliate a player is actually on within
    -- the same level/position group.
    --
    -- The is_active/is_on_secondary filter (ticket 0064 post-close
    -- correction to 0063) only applies at level 1: players.team_id alone
    -- can't distinguish a real 40-man/active MLB player from one merely
    -- administratively parked under the parent org's team_id with no real
    -- minor-league assignment (confirmed real case: 16-18-year-old
    -- international-complex signees, since this save has no real
    -- "International Complex" team to assign them to -- both look
    -- identical via team_id/level alone). A real minor-league affiliate
    -- player (level != 1) legitimately has is_active = 0 too, so the
    -- filter would incorrectly drop real AAA/AA/A/Rookie rosters if
    -- applied there -- it's scoped to level = 1 only.
    SELECT p.player_id, p.first_name, p.last_name, p.team_id, p.position,
           ot.level, t.abbr AS team_abbr
    FROM players p
    JOIN org_teams ot ON ot.team_id = p.team_id
    JOIN teams t ON t.team_id = p.team_id
    LEFT JOIN players_service_time st ON st.player_id = p.player_id
    WHERE ot.level != 1 OR st.is_active = 1 OR st.is_on_secondary = 1
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

roster_war AS (
    SELECT
        r.player_id,
        r.level,
        CASE
            WHEN brv.WAR IS NOT NULL AND prv.WAR IS NOT NULL THEN NULL
            ELSE COALESCE(brv.WAR, prv.WAR)
        END AS war
    FROM roster r
    JOIN rating rt ON rt.player_id = r.player_id
    LEFT JOIN players_run_value brv ON brv.rating_id = rt.rating_id
    LEFT JOIN players_pitching_run_value prv ON prv.rating_id = rt.rating_id
),

-- Every player at AAA/AA (level 2 or 3) across the *whole league*, not
-- just this org -- the comparison pool the promotion-candidate percentile
-- is computed against.
league_level_war AS (
    SELECT
        t.level,
        CASE
            WHEN brv.WAR IS NOT NULL AND prv.WAR IS NOT NULL THEN NULL
            ELSE COALESCE(brv.WAR, prv.WAR)
        END AS war
    FROM players p
    JOIN teams t ON t.team_id = p.team_id
    JOIN players_rating pr ON pr.player_id = p.player_id
    JOIN (
        SELECT player_id, MAX(rating_date) AS rating_date
        FROM players_rating
        GROUP BY player_id
    ) lr ON lr.player_id = pr.player_id AND lr.rating_date = pr.rating_date
    LEFT JOIN players_run_value brv ON brv.rating_id = pr.rating_id
    LEFT JOIN players_pitching_run_value prv ON prv.rating_id = pr.rating_id
    WHERE t.level IN (2, 3)
)

SELECT
    r.player_id,
    r.first_name,
    r.last_name,
    r.team_id,
    r.team_abbr,
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
    rw.war,
    CASE
        WHEN r.level NOT IN (2, 3) OR rw.war IS NULL THEN FALSE
        ELSE (
            SELECT COUNT(*) * 1.0 FROM league_level_war lw
            WHERE lw.level = r.level AND lw.war IS NOT NULL AND lw.war < rw.war
        ) / (
            SELECT COUNT(*) FROM league_level_war lw
            WHERE lw.level = r.level AND lw.war IS NOT NULL
        ) >= 0.8
    END AS is_promotion_candidate
FROM roster r
JOIN rating rt ON rt.player_id = r.player_id
JOIN roster_war rw ON rw.player_id = r.player_id
LEFT JOIN players_pitching pp ON pp.rating_id = rt.rating_id;
