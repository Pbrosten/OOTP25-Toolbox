import logging

from app.player_projection import BatterProjection

logger = logging.getLogger("app.db.projection")

proj_scripts = {
    "offense": """
        INSERT IGNORE INTO players_batting_expected
        (rating_id, PA, AB, H, `1B`, `2B`, `3B`, HR, BB, HBP, K, AVG, OBP, SLG, wOBA)
        VALUES (%(rating_id)s, %(PA)s, %(AB)s, %(H)s, %(_1B)s, %(_2B)s, %(_3B)s, %(HR)s, %(BB)s, %(HBP)s, %(K)s, %(AVG)s, %(OBP)s, %(SLG)s, %(wOBA)s)
    """,
    "basepath": """
        INSERT IGNORE INTO players_basepath_expected
        (rating_id, SB, CS) VALUES (%(rating_id)s, %(SB)s, %(CS)s)
    """,
    "defense": """
        INSERT IGNORE INTO players_fielding_expected
        (rating_id, C, `1B`, `2B`, `3B`, SS, LF, CF, RF, DH)
        VALUES (%(rating_id)s, %(C)s, %(_1B)s, %(_2B)s, %(_3B)s, %(SS)s, %(LF)s, %(CF)s, %(RF)s, %(DH)s)
    """,
    "value": """
        INSERT IGNORE INTO players_run_value
        (rating_id, batting_runs, basepath_runs, fielding_runs, total_runs, WAR)
        VALUES (%(rating_id)s, %(wRAA)s, %(BR_runs)s, %(Def_runs)s, %(Total_runs)s, %(WAR)s)
    """,
}


def process_player(player):
    try:
        projector = BatterProjection(player)
        result = projector.calc_expected_stats()
        if result is None:
            logger.warning(f"No result for player: {player.get('rating_id')}")
        return result
    except Exception as e:
        logger.warning(f"Error processing player {player.get('rating_id')}: {e}")
        return None


def update_projection_batches(
    batches, projections=None, db=None, inject=False, final=False
):
    """
    Update projection batches in the database.

    Args:
        batches (dict): Dictionary of lists for each projection type.
        projections (list): Optional list of projection results to append.
        db: MariaDB connection object.
        inject (bool): Whether to immediately inject the batches into the DB.
        final (bool): Whether this is the final commit of all batches.
    """
    if projections:
        for projection in projections:
            for key in batches:
                value = projection.get(key)
                if value is not None:
                    batches[key].append(value)

    if inject or final:
        for key in batches:
            if batches[key]:
                with db.cursor() as cursor:
                    cursor.executemany(proj_scripts[key], batches[key])
        db.commit()

        if inject:
            return {k: [] for k in batches}

        return None

    return batches
