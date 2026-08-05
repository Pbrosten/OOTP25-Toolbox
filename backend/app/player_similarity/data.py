import os
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from typing import List, Dict, Tuple

from flask import current_app, jsonify
from app.db.connection import get_db, close_db
from app.player_similarity.config import FEATURE_NAMES_BATTER, FEATURE_WEIGHTS_BATTER

def fetch_base_embedding(rating_date: str, batter: bool=True) -> List[Dict]:
    con = get_db()
    try:
        query_script = 'get_similarity_features_batter.sql' if batter else 'get_similarity_features_pitcher.sql'
        with current_app.open_resource(os.path.join('db','sql_scripts','similarity',query_script), 'r') as f:
            cursor = con.execute(f.read(), {'rating_date': rating_date})
            rows = cursor.fetchall()
            player_embeddings = [dict(row) for row in rows]
        return player_embeddings
    finally:
        close_db()

def process_base_embedding(base_embedding: List[Dict], batter: bool=True) -> Tuple[np.ndarray, List[int]]:
    if batter:
        embedding = pd.DataFrame(base_embedding, columns=FEATURE_NAMES_BATTER)
        # Convert position to position groups (C -> -1, INF -> 0, OF -> 1)
        embedding['position'] = embedding['position'].map({'C':-1, '1B':0, '2B':0, '3B':0, 'SS':0, 'LF':1, 'CF':1, 'RF':1, 'DH':0})
        player_ids = embedding.pop('player_id').to_list()
        scaler = StandardScaler()
        scaled_embedding = scaler.fit_transform(embedding)
        weights = pd.Series(FEATURE_WEIGHTS_BATTER, index=embedding.columns)
        scaled_weighted_embedding = scaled_embedding * weights.values
    return scaled_weighted_embedding, player_ids