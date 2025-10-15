import os
import logging
import pandas as pd

from flask import Blueprint, jsonify, current_app, request
from app.db.connection import get_db, close_db
from app.player_similarity.similarity import compute_similarities

bp = Blueprint('similarity', __name__, url_prefix='/api/similarity')
logger = logging.getLogger('player_similarity')

@bp.route('/<int:player_id>', methods=['GET'])
def get_player_similarity_comp_by_id(player_id):
    threshold = float(request.args.get('threshold', 0.9))
    con = get_db()
    try:
        cursor = con.execute(
            """
            SELECT player_comp, similarity
            FROM players_similarity
            WHERE player_main = ? AND similarity > ?
            ORDER BY similarity DESC
            """,
            (player_id, threshold)
        )
        rows = cursor.fetchall()

        if rows:
            result = [
                {"player_comp": row["player_comp"], "similarity": row["similarity"]}
                for row in rows
            ]
            return jsonify(result)
        else:
            return jsonify({"error": "No similar players found"}), 404
    finally:
        close_db()