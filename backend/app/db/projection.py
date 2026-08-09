import logging

from app.player_projection import BatterProjection, PitcherProjection

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

pitching_proj_scripts = {
    "pitching": """
        INSERT IGNORE INTO players_pitching_expected
        (rating_id, PA, AB, H, HR, BB, HBP, K, BA, OBP, wOBA, IP, GS, G, RA9, ERA)
        VALUES (%(rating_id)s, %(PA)s, %(AB)s, %(H)s, %(HR)s, %(BB)s, %(HBP)s, %(K)s, %(BA)s, %(OBP)s, %(wOBA)s, %(IP)s, %(GS)s, %(G)s, %(RA9)s, %(ERA)s)
    """,
    "pitching_value": """
        INSERT IGNORE INTO players_pitching_run_value
        (rating_id, pitching_runs, baserunning_runs, total_runs, WAR)
        VALUES (%(rating_id)s, %(pitching_runs)s, %(baserunning_runs)s, %(total_runs)s, %(WAR)s)
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


def process_pitcher(pitcher):
    try:
        projector = PitcherProjection(pitcher)
        result = projector.calc_expected_stats()
        if result is None:
            logger.warning(f"No result for pitcher: {pitcher.get('rating_id')}")
        return result
    except Exception as e:
        logger.warning(f"Error processing pitcher {pitcher.get('rating_id')}: {e}")
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

    Returns:
        - If neither inject nor final: the updated batches dict.
        - If inject or final: a (batches_or_None, rows_written) tuple, where
          rows_written sums cursor.rowcount across every INSERT IGNORE
          issued in this call (rows actually written, not rows attempted).
    """
    if projections:
        for projection in projections:
            for key in batches:
                value = projection.get(key)
                if value is not None:
                    batches[key].append(value)

    if inject or final:
        rows_written = 0
        for key in batches:
            if batches[key]:
                with db.cursor() as cursor:
                    cursor.executemany(proj_scripts[key], batches[key])
                    rows_written += cursor.rowcount
        db.commit()

        if inject:
            return {k: [] for k in batches}, rows_written

        return None, rows_written

    return batches


def update_pitching_projection_batches(
    batches, projections=None, db=None, inject=False, final=False
):
    """Pitcher equivalent of update_projection_batches() -- kept as a
    separate function rather than parameterizing the batter one, since
    batters and pitchers have different input/output shapes (one projection
    key here vs. four for batters) and ticket 0026 treats this as a parallel
    code path, not a shared one.

    See update_projection_batches() for the batches/inject/final contract.
    """
    if projections:
        for projection in projections:
            for key in batches:
                value = projection.get(key)
                if value is not None:
                    batches[key].append(value)

    if inject or final:
        rows_written = 0
        for key in batches:
            if batches[key]:
                with db.cursor() as cursor:
                    cursor.executemany(pitching_proj_scripts[key], batches[key])
                    rows_written += cursor.rowcount
        db.commit()

        if inject:
            return {k: [] for k in batches}, rows_written

        return None, rows_written

    return batches
