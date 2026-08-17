import logging

from app.player_projection import BatterProjection, PitcherProjection
from app.player_projection.prospect_value import calculate_prospect_value_from_row

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
    # Ticket 0086: same shape as offense/defense/value above, populated
    # from a second BatterProjection run with talent (ceiling) grades
    # substituted for current ones -- see process_player().
    "offense_talent": """
        INSERT IGNORE INTO players_batting_expected_talent
        (rating_id, PA, AB, H, `1B`, `2B`, `3B`, HR, BB, HBP, K, AVG, OBP, SLG, wOBA)
        VALUES (%(rating_id)s, %(PA)s, %(AB)s, %(H)s, %(_1B)s, %(_2B)s, %(_3B)s, %(HR)s, %(BB)s, %(HBP)s, %(K)s, %(AVG)s, %(OBP)s, %(SLG)s, %(wOBA)s)
    """,
    "defense_talent": """
        INSERT IGNORE INTO players_fielding_expected_talent
        (rating_id, C, `1B`, `2B`, `3B`, SS, LF, CF, RF, DH)
        VALUES (%(rating_id)s, %(C)s, %(_1B)s, %(_2B)s, %(_3B)s, %(SS)s, %(LF)s, %(CF)s, %(RF)s, %(DH)s)
    """,
    "value_talent": """
        INSERT IGNORE INTO players_run_value_talent
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
    # Ticket 0086: same shape as pitching/pitching_value above, populated
    # from a second PitcherProjection run with talent (ceiling) grades
    # substituted for current ones -- see process_pitcher().
    "pitching_talent": """
        INSERT IGNORE INTO players_pitching_expected_talent
        (rating_id, PA, AB, H, HR, BB, HBP, K, BA, OBP, wOBA, IP, GS, G, RA9, ERA)
        VALUES (%(rating_id)s, %(PA)s, %(AB)s, %(H)s, %(HR)s, %(BB)s, %(HBP)s, %(K)s, %(BA)s, %(OBP)s, %(wOBA)s, %(IP)s, %(GS)s, %(G)s, %(RA9)s, %(ERA)s)
    """,
    "pitching_value_talent": """
        INSERT IGNORE INTO players_pitching_run_value_talent
        (rating_id, pitching_runs, baserunning_runs, total_runs, WAR)
        VALUES (%(rating_id)s, %(pitching_runs)s, %(baserunning_runs)s, %(total_runs)s, %(WAR)s)
    """,
}

# Ticket 0075: single-table equivalent of proj_scripts/pitching_proj_scripts,
# persisting ticket 0068's FV/value calc for the league-wide leaderboard
# (0074/0076) instead of recomputing it at request time. Kept as its own
# one-key dict (rather than inlining a plain list-batching helper) to
# reuse the exact same batches/inject/final contract
# update_projection_batches()/update_pitching_projection_batches() already
# establish -- app/db/update.py's insert_prospect_values() calls this the
# same way insert_projections()/insert_pitcher_projections() do.
prospect_value_proj_scripts = {
    "prospect_value": """
        INSERT IGNORE INTO players_prospect_value
        (rating_id, fv, surplus_value, expected_war, star_odds, current_fv, risk_tag)
        VALUES (%(rating_id)s, %(fv)s, %(surplus_value)s, %(expected_war)s, %(star_odds)s, %(current_fv)s, %(risk_tag)s)
    """,
}


def process_player(player):
    try:
        projector = BatterProjection(player)
        result = projector.calc_expected_stats()
        if result is None:
            logger.warning(f"No result for player: {player.get('rating_id')}")
            return None
    except Exception as e:
        logger.warning(f"Error processing player {player.get('rating_id')}: {e}")
        return None

    # Ticket 0086: a second BatterProjection run with players_batting_talent/
    # players_fielding_position_talent's ceiling grades (get_projection_
    # inputs.sql's t_* columns) substituted for the current ones, feeding
    # the "potential" percentile bars. A failure here shouldn't drop the
    # player's real current-rating projection above, so it's a separate
    # try/except that just omits the *_talent keys on failure.
    try:
        talent_input = {
            **player,
            "babip": player.get("t_babip"),
            "gap": player.get("t_gap"),
            "eye": player.get("t_eye"),
            "strikeouts": player.get("t_strikeouts"),
            "power": player.get("t_power"),
            "pos2": player.get("t_pos2"),
            "pos3": player.get("t_pos3"),
            "pos4": player.get("t_pos4"),
            "pos5": player.get("t_pos5"),
            "pos6": player.get("t_pos6"),
            "pos7": player.get("t_pos7"),
            "pos8": player.get("t_pos8"),
            "pos9": player.get("t_pos9"),
        }
        talent_result = BatterProjection(talent_input).calc_expected_stats()
        if talent_result is not None:
            result["offense_talent"] = talent_result["offense"]
            result["defense_talent"] = talent_result["defense"]
            result["value_talent"] = talent_result["value"]
    except Exception as e:
        logger.warning(f"Error computing potential projection for player {player.get('rating_id')}: {e}")

    return result


def process_pitcher(pitcher):
    try:
        projector = PitcherProjection(pitcher)
        result = projector.calc_expected_stats()
        if result is None:
            logger.warning(f"No result for pitcher: {pitcher.get('rating_id')}")
            return None
    except Exception as e:
        logger.warning(f"Error processing pitcher {pitcher.get('rating_id')}: {e}")
        return None

    # Ticket 0086: second PitcherProjection run with players_pitching_
    # talent's ceiling grades (get_pitcher_projection_inputs.sql's t_*
    # columns) substituted for the current ones. Same isolated try/except
    # as process_player() above.
    try:
        talent_input = {
            **pitcher,
            "stuff": pitcher.get("t_stuff"),
            "control": pitcher.get("t_control"),
            "pbabip": pitcher.get("t_pbabip"),
            "hra": pitcher.get("t_hra"),
        }
        talent_result = PitcherProjection(talent_input).calc_expected_stats()
        if talent_result is not None:
            result["pitching_talent"] = talent_result["pitching"]
            result["pitching_value_talent"] = talent_result["pitching_value"]
    except Exception as e:
        logger.warning(f"Error computing potential projection for pitcher {pitcher.get('rating_id')}: {e}")

    return result


def process_prospect(row):
    """Ticket 0075: heap-processing equivalent of app/api/prospects.py's
    _value_for() -- runs the same shared calculate_prospect_value_from_row()
    (prospect_value.py) but persists the result instead of returning it
    from a request. Same try/except-and-log convention as process_player/
    process_pitcher -- a projection failure or missing input is "no
    result" for this player, not a fatal error for the whole heap.

    row: a get_prospect_value_inputs.sql row (same shape get_prospects.sql
    produces, position-gated the same way).
    """
    try:
        result = calculate_prospect_value_from_row(row)
    except Exception as e:
        logger.warning(f"Error processing prospect value for player {row.get('player_id')}: {e}")
        return None

    if result is None:
        logger.warning(f"No prospect value result for player: {row.get('player_id')}")
        return None

    return {
        "prospect_value": {
            "rating_id": row["rating_id"],
            "fv": result["fv"],
            "surplus_value": result["surplus_value"],
            "expected_war": result["expected_war"],
            "star_odds": result["star_odds"],
            "current_fv": result["current_fv"],
            "risk_tag": result["risk_tag"],
        }
    }


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


def update_prospect_value_batches(
    batches, projections=None, db=None, inject=False, final=False
):
    """Prospect-value equivalent of update_projection_batches() (ticket
    0075) -- single "prospect_value" key, one target table
    (players_prospect_value). See update_projection_batches() for the
    batches/inject/final contract.
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
                    cursor.executemany(prospect_value_proj_scripts[key], batches[key])
                    rows_written += cursor.rowcount
        db.commit()

        if inject:
            return {k: [] for k in batches}, rows_written

        return None, rows_written

    return batches
