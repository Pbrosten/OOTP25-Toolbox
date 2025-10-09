import os

from flask import Blueprint, jsonify, current_app, request
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
        cursor = con.execute("SELECT * FROM players_batting_expected WHERE rating_id = ?", (rating_id,))
        row = cursor.fetchone()
        if row:
            return jsonify(dict(row))
        else:
            return jsonify({"error": "Player projection not found"}), 404
    finally:
        close_db()

@bp.route('/batting/<int:rating_id>/percentiles', methods=['GET'])
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
        is_mlb = request.args.get('mlb', 'false').lower() == 'true'
        with current_app.open_resource(os.path.join('db', 'sql_scripts', 'api', 'get_player_expected_batting_percentiles.sql'), 'r') as f:
            cursor = con.execute(f.read(), {'rating_id':rating_id, 'is_mlb':is_mlb})
            columns = [desc[0] for desc in cursor.description]
            row = cursor.fetchone()
            result = dict(zip(columns, row))
            return jsonify(result)

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
        cursor = con.execute("SELECT * FROM players_basepath_expected WHERE rating_id = ?", (rating_id,))
        row = cursor.fetchone()
        if row:
            return jsonify(dict(row))
        else:
            return jsonify({"error": "Player projection not found"}), 404
    finally:
        close_db()

@bp.route('/basepath/<int:rating_id>/percentiles', methods=['GET'])
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
        is_mlb = request.args.get('mlb', 'false').lower() == 'true'
        with current_app.open_resource(os.path.join('db', 'sql_scripts', 'api', 'get_player_expected_basepath_percentiles.sql'), 'r') as f:
            cursor = con.execute(f.read(), {'rating_id':rating_id, 'is_mlb':is_mlb})
            columns = [desc[0] for desc in cursor.description]
            row = cursor.fetchone()
            result = dict(zip(columns, row))
            return jsonify(result)

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
        cursor = con.execute("SELECT * FROM players_fielding_expected WHERE rating_id = ?", (rating_id,))
        row = cursor.fetchone()
        if row:
            return jsonify(dict(row))
        else:
            return jsonify({"error": "Player projection not found"}), 404
    finally:
        close_db()

@bp.route('/fielding/<int:rating_id>/percentiles', methods=['GET'])
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
        is_mlb = request.args.get('mlb', 'false').lower() == 'true'
        with current_app.open_resource(os.path.join('db', 'sql_scripts', 'api', 'get_player_expected_fielding_percentiles.sql'), 'r') as f:
            cursor = con.execute(f.read(), {'rating_id':rating_id, 'is_mlb':is_mlb})
            columns = [desc[0] for desc in cursor.description]
            row = cursor.fetchone()
            result = dict(zip(columns, row))
            return jsonify(result)

    finally:
        close_db()

@bp.route('/value/<int:rating_id>/percentiles', methods=['GET'])
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
        is_mlb = request.args.get('mlb', 'false').lower() == 'true'
        with current_app.open_resource(os.path.join('db', 'sql_scripts', 'api', 'get_player_expected_value_percentiles.sql'), 'r') as f:
            cursor = con.execute(f.read(), {'rating_id':rating_id, 'is_mlb':is_mlb})
            columns = [desc[0] for desc in cursor.description]
            row = cursor.fetchone()
            result = dict(zip(columns, row))
            return jsonify(result)

    finally:
        close_db()