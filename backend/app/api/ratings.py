import os

from flask import Blueprint, jsonify, current_app
from app.db.connection import get_db, close_db

bp = Blueprint("ratings", __name__, url_prefix="/api/players/ratings")


################################# RATINGS ##################################
@bp.route("", methods=["GET"])
def get_ratings():
    """
    Retrieve all player rating entries.

    Returns:
        JSON response:
            - A list of all player ratings in the database.
    """
    con = get_db()
    try:
        with con.cursor() as cursor:
            cursor.execute("SELECT * FROM players_rating")
            rows = cursor.fetchall()
            return jsonify(rows)
    finally:
        close_db()


@bp.route("/<int:rating_id>", methods=["GET"])
def get_rating_by_id(rating_id):
    """
    Retrieve a specific player rating entry by its rating ID.

    Args:
        rating_id (int): The unique ID of the rating entry.

    Returns:
        JSON response:
            - The rating entry if found.
            - 404 error if not found.
    """
    con = get_db()
    try:
        with con.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM players_rating WHERE rating_id = %s", (rating_id,)
            )
            row = cursor.fetchone()
            if row:
                return jsonify(row)
            else:
                return jsonify({"error": "Rating not found"}), 404
    finally:
        close_db()


################################# BATTING ##################################
@bp.route("/batting", methods=["GET"])
def get_batting_ratings():
    """
    Retrieve all player batting rating entries.

    Returns:
        JSON response:
            - A list of all player batting ratings in the database.
    """
    con = get_db()
    try:
        with con.cursor() as cursor:
            cursor.execute("SELECT * FROM players_batting")
            rows = cursor.fetchall()
            return jsonify(rows)
    finally:
        close_db()


@bp.route("/<int:rating_id>/batting", methods=["GET"])
def get_batting_rating_by_id(rating_id):
    """
    Retrieve a specific player batting rating entry by its rating ID.

    Args:
        rating_id (int): The unique ID of the rating entry.

    Returns:
        JSON response:
            - The batting rating entry if found.
            - 404 error if not found.
    """
    con = get_db()
    try:
        with con.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM players_batting WHERE rating_id = %s", (rating_id,)
            )
            row = cursor.fetchone()
            if row:
                return jsonify(row)
            else:
                return jsonify({"error": "Rating not found"}), 404
    finally:
        close_db()


################################# BASEPATH #################################
@bp.route("/basepath", methods=["GET"])
def get_basepath_ratings():
    """
    Retrieve all player basepath rating entries.

    Returns:
        JSON response:
            - A list of all player basepath ratings in the database.
    """
    con = get_db()
    try:
        with con.cursor() as cursor:
            cursor.execute("SELECT * FROM players_basepath")
            rows = cursor.fetchall()
            return jsonify(rows)
    finally:
        close_db()


@bp.route("/<int:rating_id>/basepath", methods=["GET"])
def get_basepath_rating_by_id(rating_id):
    """
    Retrieve a specific player basepath rating entry by its rating ID.

    Args:
        rating_id (int): The unique ID of the rating entry.

    Returns:
        JSON response:
            - The basepath rating entry if found.
            - 404 error if not found.
    """
    con = get_db()
    try:
        with con.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM players_basepath WHERE rating_id = %s", (rating_id,)
            )
            row = cursor.fetchone()
            if row:
                return jsonify(row)
            else:
                return jsonify({"error": "Rating not found"}), 404
    finally:
        close_db()


################################# FIELDING #################################
@bp.route("/fielding", methods=["GET"])
def get_fielding_ratings():
    """
    Retrieve all player fielding rating entries.

    Returns:
        JSON response:
            - A list of all player fielding ratings in the database.
    """
    con = get_db()
    try:
        with con.cursor() as cursor:
            cursor.execute("SELECT * FROM players_fielding")
            rows = cursor.fetchall()
            return jsonify(rows)
    finally:
        close_db()


@bp.route("/<int:rating_id>/fielding", methods=["GET"])
def get_fielding_rating_by_id(rating_id):
    """
    Retrieve a specific player fielding rating entry by its rating ID.

    Args:
        rating_id (int): The unique ID of the rating entry.

    Returns:
        JSON response:
            - The fielding rating entry if found.
            - 404 error if not found.
    """
    con = get_db()
    try:
        with con.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM players_fielding WHERE rating_id = %s", (rating_id,)
            )
            row = cursor.fetchone()
            if row:
                return jsonify(row)
            else:
                return jsonify({"error": "Rating not found"}), 404
    finally:
        close_db()


@bp.route("/positions", methods=["GET"])
def get_position_ratings():
    """
    Retrieve all player position rating entries.

    Returns:
        JSON response:
            - A list of all player position ratings in the database.
    """
    con = get_db()
    try:
        with con.cursor() as cursor:
            cursor.execute("SELECT * FROM players_fielding_position")
            rows = cursor.fetchall()
            return jsonify(rows)
    finally:
        close_db()


@bp.route("/<int:rating_id>/positions", methods=["GET"])
def get_position_rating_by_id(rating_id):
    """
    Retrieve a specific player position rating entry by its rating ID.

    Args:
        rating_id (int): The unique ID of the rating entry.

    Returns:
        JSON response:
            - The position rating entry if found.
            - 404 error if not found.
    """
    con = get_db()
    try:
        with con.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM players_fielding_position WHERE rating_id = %s",
                (rating_id,),
            )
            row = cursor.fetchone()
            if row:
                return jsonify(row)
            else:
                return jsonify({"error": "Rating not found"}), 404
    finally:
        close_db()


############################### PITCH REPERTOIRE ############################
@bp.route("/pitch_repertoire", methods=["GET"])
def get_pitch_repertoire():
    """
    Retrieve all pitch repertoire entries (one row per pitch type a player
    throws).

    Returns:
        JSON response:
            - A list of all pitch repertoire entries in the database.
    """
    con = get_db()
    try:
        with con.cursor() as cursor:
            cursor.execute("SELECT * FROM players_pitch_repertoire")
            rows = cursor.fetchall()
            return jsonify(rows)
    finally:
        close_db()


@bp.route("/<int:rating_id>/pitch_repertoire", methods=["GET"])
def get_pitch_repertoire_by_id(rating_id):
    """
    Retrieve the pitch repertoire for a specific rating ID.

    Unlike the other `/<rating_id>/...` routes in this file, `rating_id` is
    not unique in `players_pitch_repertoire` (one row per pitch thrown), so
    this always returns a list -- possibly empty if the rating has no
    repertoire rows (e.g. a batter's rating_id, or a heap predating 0032) --
    never a single object or a 404.

    Args:
        rating_id (int): The unique ID of the rating entry.

    Returns:
        JSON response:
            - A list of pitch repertoire entries for the given rating ID.
    """
    con = get_db()
    try:
        with con.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM players_pitch_repertoire WHERE rating_id = %s",
                (rating_id,),
            )
            rows = cursor.fetchall()
            return jsonify(rows)
    finally:
        close_db()


########################### DEVELOPMENT TRENDS (0050) #######################
@bp.route("/<int:player_id>/trends", methods=["GET"])
def get_player_rating_trends(player_id):
    """
    Retrieve per-category rating deltas for a player: their latest heap's
    ratings vs. the ratings from 3 heaps prior, across all "overall" and
    "talent" rating tables (see ticket 0050's Design choices for the table
    list and thresholds).

    Args:
        player_id (int): The unique ID of the player.

    Returns:
        JSON response:
            - A list of `{table_name, column_name, from_date, to_date,
              from_value, to_value, delta, threshold, exceeded}` objects.
              Empty if the player has fewer than 4 recorded heaps.
            - 404 error if the player has no `players_rating` rows at all.
    """
    con = get_db()
    try:
        with con.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM players_rating WHERE player_id = %s LIMIT 1",
                (player_id,),
            )
            if cursor.fetchone() is None:
                return jsonify({"error": "Player not found"}), 404

            with current_app.open_resource(
                os.path.join(
                    "db", "sql_scripts", "api", "get_player_rating_trends.sql"
                ),
                "r",
            ) as f:
                sql = f.read()

            cursor.execute(sql, {"player_id": player_id})
            rows = cursor.fetchall()
            return jsonify(rows)
    finally:
        close_db()
