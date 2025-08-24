from flask import Blueprint, jsonify
from app.db.connection import get_db, close_db

bp = Blueprint('players', __name__, url_prefix='/api/players')

# Outline API endpoints for player data
################################# PLAYERS ##################################
@bp.route('', methods=['GET'])
def get_players():
    """
    Retrieve all player entries.

    Returns:
        JSON response:
            - A list of all player details in the database.
    """
    con = get_db()
    try:
        cursor = con.execute("SELECT * FROM players")
        rows = cursor.fetchall()
        players = [dict(row) for row in rows]
        return jsonify(players)
    finally:
        close_db()

@bp.route('/<int:player_id>', methods=['GET'])
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
        cursor = con.execute("SELECT * FROM players WHERE player_id = ?", (player_id,))
        row = cursor.fetchone()
        if row:
            return jsonify(dict(row))
        else:
            return jsonify({"error": "Player not found"}), 404
    finally:
        close_db()