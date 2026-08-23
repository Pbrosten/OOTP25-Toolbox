import os

from flask import Blueprint, jsonify, current_app
from app.db.connection import get_db, close_db

bp = Blueprint("teams", __name__, url_prefix="/api/teams")

# Levels far enough from MLB-readiness that current-rating WAR isn't a
# meaningful ranking signal (ticket 0064): BatterProjection/PitcherProjection
# compute WAR as "how good would this player be in MLB right now with his
# current ratings," with no level/league adjustment anywhere in the
# pipeline (confirmed by reading both classes) -- a fair-ish proxy for
# AAA/AA prospects close to the majors, but badly understates A-ball/
# Rookie prospects who haven't developed yet. These levels get a roster
# count per position instead of a ranked player list.
COUNT_ONLY_LEVELS = {4, 6}


@bp.route("", methods=["GET"])
def get_mlb_teams():
    """
    Retrieve every real MLB team, for the depth-chart/prospect-pipeline
    team pickers (tickets 0064/0070) -- the only places today that need to
    list teams rather than look one up by id.

    `level = 1` alone isn't enough: this save also tags 4 exhibition teams
    (AL/NL All-Stars, AL/NL Future Stars) as level 1, none of which have a
    real city (`city_id = 0`) or ever roster real players -- excluded via
    `city_id != 0`, the reliable "is this a real team" signal (division_id/
    league_id alone aren't -- real teams share division_id = 0 too).

    background_color/text_color (ticket 0073): the org's real colors, so
    `ProspectPipeline.vue` can theme its header the same way
    `TeamDepthChart.vue` already does from `get_org_depth_chart.sql` --
    added here rather than a new endpoint since this route already reads
    from `teams` and every consumer of this list (both pickers) already
    fetches it regardless.

    Returns:
        JSON response: a list of {team_id, name, abbr, nickname,
        background_color, text_color}, sorted by name.
    """
    con = get_db()
    try:
        with con.cursor() as cursor:
            cursor.execute(
                "SELECT team_id, name, abbr, nickname, background_color, text_color "
                "FROM teams WHERE level = 1 AND city_id != 0 ORDER BY name"
            )
            rows = cursor.fetchall()
        return jsonify(rows)
    finally:
        close_db()


@bp.route("/<int:team_id>/depth-chart", methods=["GET"])
def get_team_depth_chart(team_id):
    """
    Retrieve an MLB team's full organizational depth chart (ticket 0063):
    its MLB roster plus its AAA/AA/A/Rookie affiliates
    (teams.parent_team_id/level, ticket 0062), grouped by level and
    position (pitchers split into SP/RP), ranked by projected WAR
    descending within each group.

    Args:
        team_id (int): The MLB team's id. Must be a level-1 (MLB) team --
            an individual affiliate's own team_id is not a valid depth-
            chart root.

    Returns:
        JSON response:
            - 404 if team_id isn't a real level-1 MLB team.
            - {"team_id": ..., "team_name": ..., "background_color": ...,
              "text_color": ..., "levels": {level: {group: ...}}}
              otherwise, where `background_color`/`text_color` are the
              MLB team's real colors (`teams.background_color`/
              `text_color`, ticket 0064) for frontend theming, `level` is
              the raw teams.level int (1/2/3/4/6 -- 5 is excluded, see
              ticket 0062) and `group` is a position code (e.g. "1B",
              "SS") or "SP"/"RP" for pitchers.
              For levels 1/2/3 (MLB/AAA/AA), `group` maps to a WAR-sorted
              list of player entries: player_id, first_name, last_name,
              team_id, team_abbr (distinguishes affiliates sharing a
              level), war (batting + pitching WAR summed for a two-way
              player, per user request -- see get_org_depth_chart.sql;
              null only for a player with no current rating at all),
              is_promotion_candidate (top 20% of
              WAR at that level *league-wide*, AAA/AA only -- see
              get_org_depth_chart.sql; always false at MLB).
              For levels 4/6 (A/High-A, Rookie/Complex), `group` maps to a
              plain roster-count int instead -- current-rating WAR isn't a
              meaningful ranking signal that far from MLB-readiness (ticket
              0064), so no player list or WAR is returned for these levels.
    """
    con = get_db()
    try:
        with con.cursor() as cursor:
            cursor.execute(
                "SELECT level, city_id, name, nickname, background_color, "
                "text_color FROM teams WHERE team_id = %(team_id)s",
                {"team_id": team_id},
            )
            team_row = cursor.fetchone()

        # city_id != 0 excludes the save's exhibition teams (AL/NL
        # All-Stars, AL/NL Future Stars) that are also tagged level = 1 --
        # see get_mlb_teams' docstring.
        if (
            team_row is None
            or team_row["level"] != 1
            or team_row["city_id"] == 0
        ):
            return jsonify({"error": "Team not found"}), 404

        sql_path = os.path.join(
            "db", "sql_scripts", "api", "get_org_depth_chart.sql"
        )
        with current_app.open_resource(sql_path, "r") as f:
            sql = f.read()

        with con.cursor() as cursor:
            cursor.execute(sql, {"team_id": team_id})
            rows = cursor.fetchall()

        levels: dict = {}
        for row in rows:
            level = row["level"]
            # is_twp takes priority over position (ticket 0067 post-close
            # correction): a real two-way player's listed position isn't
            # always 'P' (confirmed real case: Shohei Ohtani is 'DH' but
            # has a real players_pitching row) -- checking is_twp first
            # keeps the depth chart's grouping consistent with the player
            # page's identical is_twp check, instead of only ever
            # recognizing a TWP whose position happens to read 'P'.
            if row["is_twp"]:
                group = "TWP"
            elif row["position"] == "P":
                group = row["role_group"]
            else:
                group = row["position"]
            if level in COUNT_ONLY_LEVELS:
                counts = levels.setdefault(level, {})
                counts[group] = counts.get(group, 0) + 1
                continue
            levels.setdefault(level, {}).setdefault(group, []).append(
                {
                    "player_id": row["player_id"],
                    "first_name": row["first_name"],
                    "last_name": row["last_name"],
                    "team_id": row["team_id"],
                    "team_abbr": row["team_abbr"],
                    "war": row["war"],
                    "is_promotion_candidate": bool(row["is_promotion_candidate"]),
                }
            )

        for level, groups in levels.items():
            if level in COUNT_ONLY_LEVELS:
                continue
            for players in groups.values():
                players.sort(
                    key=lambda p: p["war"] if p["war"] is not None else float("-inf"),
                    reverse=True,
                )

        return jsonify(
            {
                "team_id": team_id,
                "team_name": f"{team_row['name']} {team_row['nickname']}".strip(),
                "background_color": team_row["background_color"],
                "text_color": team_row["text_color"],
                "levels": levels,
            }
        )
    finally:
        close_db()


@bp.route("/<int:team_id>/war-summary", methods=["GET"])
def get_team_war_summary(team_id):
    """
    Retrieve an MLB team's current-roster WAR aggregate and its power
    ranking among all real MLB teams by that same figure (ticket 0079),
    for the GM Command Center dashboard's headline stat (ticket 0038).
    Sums players_run_value.WAR (batting) + players_pitching_run_value.WAR
    (pitching) at each player's latest rating snapshot, two-way players
    counted for both sides -- same convention as get_org_depth_chart.sql
    (ticket 0063). MLB (level = 1) roster only -- full-org/affiliate WAR
    is covered in more detail by ticket 0081's per-position breakdown
    instead.

    Args:
        team_id (int): The MLB team's id. Must be a level-1 (MLB) team --
            an individual affiliate's own team_id is not valid here.

    Returns:
        JSON response:
            - 404 if team_id isn't a real level-1 MLB team.
            - {"team_id": ..., "war": ..., "rank": ..., "total_teams": ...}
              otherwise, where war is the summed team WAR (0 if the
              roster has no rated players yet), rank is this team's
              1-indexed rank by war among all real MLB teams (ties share
              a rank, per get_team_war_summary.sql's RANK() -- not
              ROW_NUMBER()), and total_teams is the league size the rank
              is out of.
    """
    con = get_db()
    try:
        with con.cursor() as cursor:
            cursor.execute(
                "SELECT level, city_id FROM teams WHERE team_id = %(team_id)s",
                {"team_id": team_id},
            )
            team_row = cursor.fetchone()

        # city_id != 0 excludes the save's exhibition teams also tagged
        # level = 1 -- see get_mlb_teams'/get_team_depth_chart's docstrings.
        if (
            team_row is None
            or team_row["level"] != 1
            or team_row["city_id"] == 0
        ):
            return jsonify({"error": "Team not found"}), 404

        sql_path = os.path.join(
            "db", "sql_scripts", "api", "get_team_war_summary.sql"
        )
        with current_app.open_resource(sql_path, "r") as f:
            sql = f.read()

        with con.cursor() as cursor:
            cursor.execute(sql, {"team_id": team_id})
            row = cursor.fetchone()

        return jsonify(
            {
                "team_id": team_id,
                "war": row["war"],
                "rank": row["team_rank"],
                "total_teams": row["total_teams"],
            }
        )
    finally:
        close_db()
