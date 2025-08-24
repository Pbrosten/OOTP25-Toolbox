from app.player_projection import BatterProjection
from flask import current_app

proj_scripts = {
    "offense": """INSERT OR IGNORE INTO players_batting_expected
        (rating_id, PA, AB, H, "1B", "2B", "3B", HR, BB, HBP, K, AVG, OBP, SLG, wOBA)
        VALUES (:rating_id, :PA, :AB, :H, :_1B, :_2B, :_3B, :HR, :BB, :HBP, :K, :AVG, :OBP, :SLG, :wOBA)""",
    "basepath": """INSERT OR IGNORE INTO players_basepath_expected
        (rating_id, SB, CS) VALUES (:rating_id, :SB, :CS)""",
    "defense": """INSERT OR IGNORE INTO players_fielding_expected
        (rating_id, C, "1B", "2B", "3B", SS, LF, CF, RF, DH)
        VALUES (:rating_id, :C, :_1B, :_2B, :_3B, :SS, :LF, :CF, :RF, :DH)""",
    "value": """INSERT OR IGNORE INTO players_run_value
        (rating_id, batting_runs, basepath_runs, fielding_runs, total_runs, WAR)
        VALUES (:rating_id, :wRAA, :BR_runs, :Def_runs, :Total_runs, :WAR)"""
}

def process_player(player):
    try:
        projector = BatterProjection(player)
        result = projector.calc_expected_stats()
        if result is None:
            current_app.logger.warning(f"No result for player: {player.get('rating_id')}")
        return result
    except Exception as e:
        current_app.logger.warning(f"Error processing player {player.get('rating_id')}: {e}")
        return None

def update_projection_batches(batches, projections=None, db=None, inject=False, final=False):
    if final:
        for key in batches:
            if batches[key]:
                db.executemany(proj_scripts[key], batches[key])
        db.commit()
        return None

    if projections:
        for projection in projections:
            for key in batches:
                value = projection.get(key)
                if value is not None:
                    batches[key].append(value)

    if inject:
        for key in batches:
            if batches[key]:
                db.executemany(proj_scripts[key], batches[key])
        db.commit()
        return {k: [] for k in batches}

    return batches
