from flask import Blueprint, jsonify
from app.db.connection import get_db, close_db

bp = Blueprint('projections', __name__, url_prefix='/api/players/stats/expected')

################################ PROJECTIONS ################################
@bp.route('/batting', methods=['GET'])
def get_expected_batting_stats():
    """
    Retrieve all player expected batting stat entries.

    Returns:
        JSON response:
            - A list of all player expected batting stats in the database.
    """
    con = get_db()
    try:
        cursor = con.execute("SELECT * FROM players_batting_expected")
        rows = cursor.fetchall()
        ratings = [dict(row) for row in rows]
        return jsonify(ratings)
    finally:
        close_db()

@bp.route('/batting/<int:rating_id>', methods=['GET'])
def get_expected_batting_stats_by_id(player_id):
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
        cursor = con.execute("SELECT * FROM players_batting_expected WHERE player_id = ?", (rating_id,))
        row = cursor.fetchone()
        if row:
            return jsonify(dict(row))
        else:
            return jsonify({"error": "Player projection not found"}), 404
    finally:
        close_db()
    
@bp.route('/basepath', methods=['GET'])
def get_expected_basepath_stats():
    """
    Retrieve all player expected basepath stat entries.

    Returns:
        JSON response:
            - A list of all player expected basepath stats in the database.
    """
    con = get_db()
    try:
        cursor = con.execute("SELECT * FROM players_basepath_expected")
        rows = cursor.fetchall()
        ratings = [dict(row) for row in rows]
        return jsonify(ratings)
    finally:
        close_db()

@bp.route('/basepath/<int:rating_id>', methods=['GET'])
def get_expected_basepath_stats_by_id(player_id):
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
        cursor = con.execute("SELECT * FROM players_basepath_expected WHERE player_id = ?", (rating_id,))
        row = cursor.fetchone()
        if row:
            return jsonify(dict(row))
        else:
            return jsonify({"error": "Player projection not found"}), 404
    finally:
        close_db()

@bp.route('/fielding', methods=['GET'])
def get_expected_fielding_stats():
    """
    Retrieve all player expected fielding stat entries.

    Returns:
        JSON response:
            - A list of all player expected fielding stats in the database.
    """
    con = get_db()
    try:
        cursor = con.execute("SELECT * FROM players_fielding_expected")
        rows = cursor.fetchall()
        ratings = [dict(row) for row in rows]
        return jsonify(ratings)
    finally:
        close_db()

@bp.route('/fielding/<int:rating_id>', methods=['GET'])
def get_expected_fielding_stats_by_id(player_id):
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
        cursor = con.execute("SELECT * FROM players_fielding_expected WHERE player_id = ?", (rating_id,))
        row = cursor.fetchone()
        if row:
            return jsonify(dict(row))
        else:
            return jsonify({"error": "Player projection not found"}), 404
    finally:
        close_db()