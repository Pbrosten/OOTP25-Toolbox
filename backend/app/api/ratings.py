from flask import Blueprint, jsonify
from app.db.connection import get_db, close_db

bp = Blueprint('ratings', __name__, url_prefix='/api/players/ratings')

################################# RATINGS ##################################
@bp.route('', methods=['GET'])
def get_ratings():
    """
    Retrieve all player rating entries.

    Returns:
        JSON response:
            - A list of all player ratings in the database.
    """
    con = get_db()
    try:
        cursor = con.execute("SELECT * FROM players_rating")
        rows = cursor.fetchall()
        ratings = [dict(row) for row in rows]
        return jsonify(ratings)
    finally:
        close_db()

@bp.route('/<int:rating_id>', methods=['GET'])
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
        cursor = con.execute("SELECT * FROM players_rating WHERE rating_id = ?", (rating_id,))
        row = cursor.fetchone()
        if row:
            return jsonify(dict(row))
        else:
            return jsonify({"error": "Rating not found"}), 404
    finally:
        close_db()

################################# BATTING ##################################
@bp.route('/batting', methods=['GET'])
def get_batting_ratings():
    """
    Retrieve all player batting rating entries.

    Returns:
        JSON response:
            - A list of all player batting ratings in the database.
    """
    con = get_db()
    try:
        cursor = con.execute("SELECT * FROM players_batting")
        rows = cursor.fetchall()
        ratings = [dict(row) for row in rows]
        return jsonify(ratings)
    finally:
        close_db()

@bp.route('/batting/<int:rating_id>', methods=['GET'])
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
        cursor = con.execute("SELECT * FROM players_batting WHERE rating_id = ?", (rating_id,))
        row = cursor.fetchone()
        if row:
            return jsonify(dict(row))
        else:
            return jsonify({"error": "Rating not found"}), 404
    finally:
        close_db()

################################# BASEPATH #################################
@bp.route('/basepath', methods=['GET'])
def get_basepath_ratings():
    """
    Retrieve all player basepath rating entries.

    Returns:
        JSON response:
            - A list of all player basepath ratings in the database.
    """
    con = get_db()
    try:
        cursor = con.execute("SELECT * FROM players_basepath")
        rows = cursor.fetchall()
        ratings = [dict(row) for row in rows]
        return jsonify(ratings)
    finally:
        close_db()

@bp.route('/basepath/<int:rating_id>', methods=['GET'])
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
        cursor = con.execute("SELECT * FROM players_basepath WHERE rating_id = ?", (rating_id,))
        row = cursor.fetchone()
        if row:
            return jsonify(dict(row))
        else:
            return jsonify({"error": "Rating not found"}), 404
    finally:
        close_db()
    
################################# FIELDING #################################
@bp.route('/fielding', methods=['GET'])
def get_fielding_ratings():
    """
    Retrieve all player fielding rating entries.

    Returns:
        JSON response:
            - A list of all player fielding ratings in the database.
    """
    con = get_db()
    try:
        cursor = con.execute("SELECT * FROM players_fielding")
        rows = cursor.fetchall()
        ratings = [dict(row) for row in rows]
        return jsonify(ratings)
    finally:
        close_db()

@bp.route('/fielding/<int:rating_id>', methods=['GET'])
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
        cursor = con.execute("SELECT * FROM players_fielding WHERE rating_id = ?", (rating_id,))
        row = cursor.fetchone()
        if row:
            return jsonify(dict(row))
        else:
            return jsonify({"error": "Rating not found"}), 404
    finally:
        close_db()

@bp.route('/positions', methods=['GET'])
def get_position_ratings():
    """
    Retrieve all player position rating entries.

    Returns:
        JSON response:
            - A list of all player position ratings in the database.
    """
    con = get_db()
    try:
        cursor = con.execute("SELECT * FROM players_fielding_position")
        rows = cursor.fetchall()
        ratings = [dict(row) for row in rows]
        return jsonify(ratings)
    finally:
        close_db()

@bp.route('/positions/<int:rating_id>', methods=['GET'])
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
        cursor = con.execute("SELECT * FROM players_fielding_position WHERE rating_id = ?", (rating_id,))
        row = cursor.fetchone()
        if row:
            return jsonify(dict(row))
        else:
            return jsonify({"error": "Rating not found"}), 404
    finally:
        close_db()
