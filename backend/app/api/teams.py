import os

from flask import Blueprint, jsonify, current_app
from app.db.connection import get_db, close_db

bp = Blueprint("teams", __name__, url_prefix="/api/teams")


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
            - {"team_id": ..., "levels": {level: {group: [players]}}}
              otherwise, where `level` is the raw teams.level int (1/2/3/
              4/6 -- 5 is excluded, see ticket 0062) and `group` is a
              position code (e.g. "1B", "SS") or "SP"/"RP" for pitchers.
              Each player entry: player_id, first_name, last_name,
              team_id, war (WAR, or null for a two-way player or a player
              with no current rating).
    """
    con = get_db()
    try:
        with con.cursor() as cursor:
            cursor.execute(
                "SELECT level FROM teams WHERE team_id = %(team_id)s",
                {"team_id": team_id},
            )
            team_row = cursor.fetchone()

        if team_row is None or team_row["level"] != 1:
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
            group = row["role_group"] if row["position"] == "P" else row["position"]
            levels.setdefault(level, {}).setdefault(group, []).append(
                {
                    "player_id": row["player_id"],
                    "first_name": row["first_name"],
                    "last_name": row["last_name"],
                    "team_id": row["team_id"],
                    "war": row["war"],
                }
            )

        for groups in levels.values():
            for players in groups.values():
                players.sort(
                    key=lambda p: p["war"] if p["war"] is not None else float("-inf"),
                    reverse=True,
                )

        return jsonify({"team_id": team_id, "levels": levels})
    finally:
        close_db()
