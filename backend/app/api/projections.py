import os
import logging

from flask import Blueprint, jsonify, current_app, request
from app.db.connection import get_db, close_db

bp = Blueprint("projections", __name__, url_prefix="/api/players/ratings")

logger = logging.getLogger("api.projections")


################################ PROJECTIONS ################################
@bp.route("/expected/batting", methods=["GET"])
def get_expected_batting_stats():
    """
    Retrieve all player expected batting stat entries.

    Returns:
        JSON response:
            - A list of all player expected batting stats in the database.
    """
    con = get_db()
    try:
        with con.cursor() as cursor:
            cursor.execute("SELECT * FROM players_batting_expected")
            rows = cursor.fetchall()
            return jsonify(rows)
    finally:
        close_db()


@bp.route("/<int:rating_id>/expected/batting", methods=["GET"])
def get_expected_batting_stats_by_id(rating_id):
    """
    Retrieve a single player batting projected stats by their unique ID.

    Args:
        player_id (int): The ID of the player to retrieve.

    Returns:
        JSON response:
            - Player projection record if found.
            - 404 error if not found.
    """
    con = get_db()
    try:
        with con.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM players_batting_expected WHERE rating_id = %s",
                (rating_id,),
            )
            row = cursor.fetchone()
            if row:
                return jsonify(row)
            else:
                return jsonify({"error": "Player projection not found"}), 404
    finally:
        close_db()


@bp.route("/<int:rating_id>/expected/batting/percentiles", methods=["GET"])
def get_expected_batting_percentiles(rating_id):
    """
    Retrieve a single player batting projected percentiles by their unique ID..

    Returns:
        JSON response:
            - Player projection record if found.
            - 404 error if not found.
    """
    con = get_db()
    try:
        is_milb = 1 if request.args.get("milb", "false").lower() == "true" else 0
        with current_app.open_resource(
            os.path.join(
                "db",
                "sql_scripts",
                "api",
                "get_player_expected_batting_percentiles.sql",
            ),
            "r",
        ) as f:
            sql = f.read()

        with con.cursor() as cursor:
            cursor.execute(sql, {"rating_id": rating_id, "is_milb": is_milb})
            row = cursor.fetchone()
        if row:
            return jsonify(row)
        else:
            return jsonify({"error": "Player projection not found"}), 404

    finally:
        close_db()


@bp.route("/expected/basepath", methods=["GET"])
def get_expected_basepath_stats():
    """
    Retrieve all player expected basepath stat entries.

    Returns:
        JSON response:
            - A list of all player expected basepath stats in the database.
    """
    con = get_db()
    try:
        with con.cursor() as cursor:
            cursor.execute("SELECT * FROM players_basepath_expected")
            rows = cursor.fetchall()
            return jsonify(rows)
    finally:
        close_db()


@bp.route("/<int:rating_id>/expected/basepath", methods=["GET"])
def get_expected_basepath_stats_by_id(rating_id):
    """
    Retrieve a single player basepath projected stats by their unique ID.

    Args:
        player_id (int): The ID of the player to retrieve.

    Returns:
        JSON response:
            - Player projection record if found.
            - 404 error if not found.
    """
    con = get_db()
    try:
        with con.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM players_basepath_expected WHERE rating_id = %s",
                (rating_id,),
            )
            row = cursor.fetchone()
            if row:
                return jsonify(row)
            else:
                return jsonify({"error": "Player projection not found"}), 404
    finally:
        close_db()


@bp.route("/<int:rating_id>/expected/basepath/percentiles", methods=["GET"])
def get_expected_basepath_percentiles(rating_id):
    """
    Retrieve a single player basepath projected percentiles by their unique ID..

    Returns:
        JSON response:
            - Player projection record if found.
            - 404 error if not found.
    """
    con = get_db()
    try:
        is_milb = 1 if request.args.get("milb", "false").lower() == "true" else 0
        with current_app.open_resource(
            os.path.join(
                "db",
                "sql_scripts",
                "api",
                "get_player_expected_basepath_percentiles.sql",
            ),
            "r",
        ) as f:
            sql = f.read()
        with con.cursor() as cursor:
            cursor.execute(sql, {"rating_id": rating_id, "is_milb": is_milb})
            row = cursor.fetchone()
            return jsonify(row)

    finally:
        close_db()


@bp.route("/expected/fielding", methods=["GET"])
def get_expected_fielding_stats():
    """
    Retrieve all player expected fielding stat entries.

    Returns:
        JSON response:
            - A list of all player expected fielding stats in the database.
    """
    con = get_db()
    try:
        with con.cursor() as cursor:
            cursor.execute("SELECT * FROM players_fielding_expected")
            rows = cursor.fetchall()
            return jsonify(rows)
    finally:
        close_db()


@bp.route("/<int:rating_id>/expected/fielding", methods=["GET"])
def get_expected_fielding_stats_by_id(rating_id):
    """
    Retrieve a single player fielding projected stats by their unique ID.

    Args:
        player_id (int): The ID of the player to retrieve.

    Returns:
        JSON response:
            - Player projection record if found.
            - 404 error if not found.
    """
    con = get_db()
    try:
        with con.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM players_fielding_expected WHERE rating_id = %s",
                (rating_id,),
            )
            row = cursor.fetchone()
            if row:
                return jsonify(row)
            else:
                return jsonify({"error": "Player projection not found"}), 404
    finally:
        close_db()


@bp.route("/<int:rating_id>/expected/fielding/percentiles", methods=["GET"])
def get_expected_fielding_percentiles(rating_id):
    """
    Retrieve a single player fielding projected percentiles by their unique ID..

    Returns:
        JSON response:
            - Player projection record if found.
            - 404 error if not found.
    """
    con = get_db()
    try:
        is_milb = 1 if request.args.get("milb", "false").lower() == "true" else 0
        with current_app.open_resource(
            os.path.join(
                "db",
                "sql_scripts",
                "api",
                "get_player_expected_fielding_percentiles.sql",
            ),
            "r",
        ) as f:
            sql = f.read()
        with con.cursor() as cursor:
            cursor.execute(sql, {"rating_id": rating_id, "is_milb": is_milb})
            row = cursor.fetchone()
            return jsonify(row)

    finally:
        close_db()


@bp.route("/expected/pitching", methods=["GET"])
def get_expected_pitching_stats():
    """
    Retrieve all player expected pitching stat entries.

    Returns:
        JSON response:
            - A list of all player expected pitching stats in the database.
    """
    con = get_db()
    try:
        with con.cursor() as cursor:
            cursor.execute("SELECT * FROM players_pitching_expected")
            rows = cursor.fetchall()
            return jsonify(rows)
    finally:
        close_db()


@bp.route("/<int:rating_id>/expected/pitching", methods=["GET"])
def get_expected_pitching_stats_by_id(rating_id):
    """
    Retrieve a single player pitching projected stats by their unique ID.

    Args:
        player_id (int): The ID of the player to retrieve.

    Returns:
        JSON response:
            - Player projection record if found.
            - 404 error if not found.
    """
    con = get_db()
    try:
        with con.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM players_pitching_expected WHERE rating_id = %s",
                (rating_id,),
            )
            row = cursor.fetchone()
            if row:
                return jsonify(row)
            else:
                return jsonify({"error": "Player projection not found"}), 404
    finally:
        close_db()


@bp.route("/<int:rating_id>/expected/pitching/percentiles", methods=["GET"])
def get_expected_pitching_percentiles(rating_id):
    """
    Retrieve a single player's pitching production and value projected
    percentiles by their unique ID (players_pitching_expected +
    players_pitching_run_value, ticket 0027).

    Returns:
        JSON response:
            - Player projection record if found.
            - 404 error if not found.
    """
    con = get_db()
    try:
        is_milb = 1 if request.args.get("milb", "false").lower() == "true" else 0
        with current_app.open_resource(
            os.path.join(
                "db",
                "sql_scripts",
                "api",
                "get_player_expected_pitching_percentiles.sql",
            ),
            "r",
        ) as f:
            sql = f.read()

        with con.cursor() as cursor:
            cursor.execute(sql, {"rating_id": rating_id, "is_milb": is_milb})
            row = cursor.fetchone()
        if row:
            return jsonify(row)
        else:
            return jsonify({"error": "Player projection not found"}), 404

    finally:
        close_db()


@bp.route("/<int:rating_id>/expected/value/percentiles", methods=["GET"])
def get_expected_value_percentiles(rating_id):
    """
    Retrieve a single player run value projected percentiles by their unique ID..

    Returns:
        JSON response:
            - Player projection record if found.
            - 404 error if not found.
    """
    con = get_db()
    try:
        is_milb = 1 if request.args.get("milb", "false").lower() == "true" else 0
        with current_app.open_resource(
            os.path.join(
                "db", "sql_scripts", "api", "get_player_expected_value_percentiles.sql"
            ),
            "r",
        ) as f:
            sql = f.read()
        with con.cursor() as cursor:
            cursor.execute(sql, {"rating_id": rating_id, "is_milb": is_milb})
            row = cursor.fetchone()
            return jsonify(row)

    finally:
        close_db()
