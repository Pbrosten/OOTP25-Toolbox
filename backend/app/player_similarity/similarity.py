import os
import logging
import pickle as pkl
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from flask import current_app
from app.db.connection import get_db
from app.player_similarity.data import fetch_base_embedding, process_base_embedding

logger = logging.getLogger('player_similarity')

def compute_similarities(rating_date: str, batter=True) -> None:
    player_type = 'batter' if batter else 'pitcher'
    base_embedding = fetch_base_embedding(rating_date=rating_date, batter=batter)
    embedding, player_ids = process_base_embedding(base_embedding=base_embedding, batter=batter)

    logger.info('Running cosine similarities')
    similarity_matrix = cosine_similarity(embedding)
    normalized_similarity = (similarity_matrix + 1) / 2

    logger.info(f'Computed similarities for {normalized_similarity.shape[0]} players')
    save_similarity_to_db(similarity_matrix=similarity_matrix, player_ids=player_ids, player_type=player_type)
    return None

def save_similarity_to_db(similarity_matrix, player_ids, player_type) -> None:
    con = get_db()
    
    rows = []
    for i, name_1 in enumerate(player_ids):
        for j, name_2 in enumerate(player_ids):
            if i != j:
                sim = float(similarity_matrix[i, j])
                rows.append((name_1, name_2, sim, player_type))
    logger.info(f'Injecting {len(rows)} similarity scores')
    con.executemany('''
        INSERT OR REPLACE INTO players_similarity (player_main, player_comp, similarity, player_type)
        VALUES (?, ?, ?, ?)
    ''', rows)

    con.commit()
    con.close()