import os
import logging
import pandas as pd

from flask import Blueprint, jsonify, current_app, request
from app.db.connection import get_db, close_db

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
            cursor.execute(
                """
                SELECT p.player_id, p.first_name, p.last_name, p.position, p.retired, t.abbr AS team_abbr
                FROM players AS p
                LEFT JOIN teams AS t ON p.team_id = t.team_id
                WHERE CONCAT(p.first_name, ' ', p.last_name) LIKE %s
            """,
                ("%" + query + "%",),
            )
            rows = cursor.fetchall()
            players = [dict(row) for row in rows]
            return jsonify(players[:10])
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
