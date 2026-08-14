import os
import logging
import pandas as pd

from flask import Blueprint, jsonify, current_app, request
from app.db.connection import get_db, close_db
from app.player_projection.contract_value import calculate_surplus_value

bp = Blueprint("players", __name__, url_prefix="/api/players")


# Outline API endpoints for player data
################################# PLAYERS ##################################
@bp.route("", methods=["GET"])
def get_players():
    """
    Retrieve all player entries.

    Returns:
        JSON response:
            - A list of all player details in the database.
    """
    con = get_db()
    try:
        with con.cursor() as cursor:
            cursor.execute("SELECT * FROM players")
            rows = cursor.fetchall()
            players = [dict(row) for row in rows]
            return jsonify(players)
    finally:
        close_db()


@bp.route("/<int:player_id>", methods=["GET"])
def get_player_by_id(player_id):
    """
    Retrieve a single player by their unique ID.

    Args:
        player_id (int): The ID of the player to retrieve.

    Returns:
        JSON response:
            - Player record if found.
            - 404 error if not found.
    """
    con = get_db()
    try:
        with con.cursor() as cursor:
            cursor.execute("SELECT * FROM players WHERE player_id = %s", (player_id,))
            row = cursor.fetchone()
            if row:
                return jsonify(row)
            else:
                return jsonify({"error": "Player not found"}), 404
    finally:
        close_db()


@bp.route("/search", methods=["GET"])
def search_players():
    """
    Search for players based on a query string.

    Query Parameters:
        - q (str): The search query.

    Returns:
        JSON response:
            - A list of players matching the search query.
    """
    query = request.args.get("q", "")
    con = get_db()
    try:
        with con.cursor() as cursor:
            # Ranked by career WAR (batting vs. pitching, whichever half of
            # a player's career carries their value) as a "fame weight",
            # so an established player outranks an obscure one sharing a
            # name -- see ticket 0047. Missing WAR (no career-stat rows at
            # all) sorts last via the 0 fallback, not first/erroring.
            cursor.execute(
                """
                SELECT p.player_id, p.first_name, p.last_name, p.position, p.retired, t.abbr AS team_abbr
                FROM players AS p
                LEFT JOIN teams AS t ON p.team_id = t.team_id
                LEFT JOIN (
                    SELECT player_id, SUM(war) AS total_war
                    FROM players_career_batting_stats
                    GROUP BY player_id
                ) AS bw ON bw.player_id = p.player_id
                LEFT JOIN (
                    SELECT player_id, SUM(war) AS total_war
                    FROM players_career_pitching_stats
                    GROUP BY player_id
                ) AS pw ON pw.player_id = p.player_id
                WHERE CONCAT(p.first_name, ' ', p.last_name) LIKE %s
                ORDER BY
                    CASE
                        WHEN bw.total_war IS NULL AND pw.total_war IS NULL THEN 0
                        WHEN bw.total_war IS NULL THEN pw.total_war
                        WHEN pw.total_war IS NULL THEN bw.total_war
                        ELSE GREATEST(bw.total_war, pw.total_war)
                    END DESC
                LIMIT 10
            """,
                ("%" + query + "%",),
            )
            rows = cursor.fetchall()
            players = [dict(row) for row in rows]
            return jsonify(players)
    finally:
        close_db()


@bp.route("/<int:player_id>/details", methods=["GET"])
def get_player_details_by_id(player_id):
    """
    Retrieve the player details for a single player by their unique ID.
    This consists of:
        - player name
        - team name
        - position
        - batting handedness
        - throwing handedness
        - height
        - weight
        - age
        - batting stats for last three seasons
        - aggregate batting stats

    Args:
        player_id (int): The ID of the player to retrieve.

    Returns:
        JSON response:
            - Player record if found.
            - 404 error if not found.
    """
    con = get_db()
    try:
        with current_app.open_resource(
            os.path.join("db", "sql_scripts", "api", "get_player_details.sql"), "r"
        ) as f:
            with con.cursor() as cursor:
                cursor.execute(f.read(), (player_id,))
                row = cursor.fetchone()
                if row:
                    return jsonify(row)
                else:
                    return jsonify({"error": "Player not found"}), 404
    finally:
        close_db()


@bp.route("/<int:player_id>/career/batting", methods=["GET"])
def get_player_career_batting(player_id):
    """
    Retrieve the player career batting statistics for a single player by their unique ID.

    Args:
        player_id (int): The ID of the player to retrieve.

    Returns:
        JSON response:
            - Player career batting records if found.
            - 404 error if not found.
    """
    con = get_db()
    try:
        with con.cursor() as cursor:
            check_query = """
                SELECT 1
                FROM players_career_batting_stats
                WHERE player_id = %s AND split_id = 1 AND league_id = 203
                LIMIT 1
            """
            cursor.execute(check_query, (player_id,))
            has_mlb_stats = cursor.fetchone() is not None

            sql_file = (
                "get_player_career_batting_mlb.sql"
                if has_mlb_stats
                else "get_player_career_batting_milb.sql"
            )

            sql_path = os.path.join("db", "sql_scripts", "api", sql_file)
            with current_app.open_resource(sql_path, "r") as f:
                query = f.read()
                cursor.execute(query, (player_id,))
                rows = cursor.fetchall()

                if rows:
                    return jsonify(rows)
                else:
                    return jsonify({"error": "Player not found"}), 404
    finally:
        close_db(con)


@bp.route("/<int:player_id>/career/pitching", methods=["GET"])
def get_player_career_pitching(player_id):
    """
    Retrieve the player career pitching statistics for a single player by their unique ID.

    Args:
        player_id (int): The ID of the player to retrieve.

    Returns:
        JSON response:
            - Player career pitching records if found.
            - 404 error if not found.
    """
    con = get_db()
    try:
        with con.cursor() as cursor:
            check_query = """
                SELECT 1
                FROM players_career_pitching_stats
                WHERE player_id = %s AND split_id = 1 AND league_id = 203
                LIMIT 1
            """
            cursor.execute(check_query, (player_id,))
            has_mlb_stats = cursor.fetchone() is not None

            sql_file = (
                "get_player_career_pitching_mlb.sql"
                if has_mlb_stats
                else "get_player_career_pitching_milb.sql"
            )

            sql_path = os.path.join("db", "sql_scripts", "api", sql_file)
            with current_app.open_resource(sql_path, "r") as f:
                query = f.read()
                cursor.execute(query, (player_id,))
                rows = cursor.fetchall()

                if rows:
                    return jsonify(rows)
                else:
                    return jsonify({"error": "Player not found"}), 404
    finally:
        close_db(con)


@bp.route("/<int:player_id>/ratings", methods=["GET"])
def get_player_ratings(player_id):
    """
    Retrieve the player rating ids for a single player by their unique id.

    Query Args:
        - latest (bool): Return only the most recent rating
        - years (bool): Return the most recent rating for each year

    Returns:
        JSON response:
            - List of rating ids if found.
            - Singleton rating dict if latest is true.
            - 404 error if not found.
    """
    logger = logging.getLogger("api-testing")
    con = get_db()

    try:
        # Query params
        latest = request.args.get("latest", "false").lower() == "true"
        years = request.args.get("years", "false").lower() == "true"

        # Load SQL from file
        sql_path = os.path.join("db", "sql_scripts", "api", "get_player_ratings.sql")
        with current_app.open_resource(sql_path, mode="r") as f:
            sql = f.read()

        with con.cursor() as cursor:
            cursor.execute(sql, (player_id,))
            rows = cursor.fetchall()

        if rows:
            if latest:
                return jsonify(rows[0])
            elif years:
                seen_years = set()
                filtered = []
                for row in rows:
                    year = row["rating_date"].year
                    if year not in seen_years:
                        seen_years.add(year)
                        filtered.append(row)
                return jsonify(filtered)
            else:
                return jsonify(rows)
        else:
            logger.warning(f"[404] No ratings found for player_id={player_id}")
            return jsonify({"error": "Player ratings not found"}), 404

    finally:
        close_db(con)


@bp.route("/<int:player_id>/surplus-value", methods=["GET"])
def get_player_surplus_value(player_id):
    """
    Retrieve a player's projected surplus value (ticket 0056): fair value
    over their years of control minus what they're actually owed.

    Returns:
        JSON response:
            - {"available": False} if the player is two-way (0028's
              never-net-batting/pitching-WAR precedent), has no current
              WAR projection, or has neither a contract nor a service-time
              record on file.
            - {"available": True, "years": [...], "total_value": ...,
              "total_cost": ..., "total_surplus": ...} otherwise.
    """
    con = get_db()
    try:
        sql_path = os.path.join(
            "db", "sql_scripts", "api", "get_player_contract_inputs.sql"
        )
        with current_app.open_resource(sql_path, "r") as f:
            sql = f.read()

        with con.cursor() as cursor:
            cursor.execute(sql, {"player_id": player_id})
            row = cursor.fetchone()

        if row is None:
            return jsonify({"available": False})

        batting_war = row["batting_war"]
        pitching_war = row["pitching_war"]
        two_way = batting_war is not None and pitching_war is not None
        base_war = batting_war if batting_war is not None else pitching_war

        # years=0/current_year=0 is a real row OOTP writes for every
        # unsigned player (a placeholder, not a 1-year $0 contract) --
        # current_year=0 would also wrap Python's salaries[-1] indexing in
        # calculate_surplus_value, so this must be filtered here, not just
        # treated as "no row".
        has_contract = row["years"] is not None and row["years"] > 0
        has_service_time = row["mlb_service_years"] is not None

        if (
            two_way
            or base_war is None
            or row["age"] is None
            or not (has_contract or has_service_time)
        ):
            return jsonify({"available": False})

        result = calculate_surplus_value(
            base_war=base_war,
            current_age=row["age"],
            mlb_service_years=row["mlb_service_years"] or 0,
            contract=row if has_contract else None,
        )
        if result is None:
            return jsonify({"available": False})

        return jsonify({"available": True, **result})
    finally:
        close_db()
