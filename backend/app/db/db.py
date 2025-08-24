# import os
# import re
# import sys
# import sqlite3
# import click

# from typing import Optional
# from datetime import datetime
# from pathlib import Path
# from flask import current_app, g
# from tqdm import tqdm
# from multiprocessing import Pool, cpu_count

# sys.path.append(str(Path(__file__).resolve().parents[3]))
# from player_projection import BatterProjection

# DUMP_INCLUSION_LIST = [
#     'cities', 'continents', 'divisions', 'language_data', 'languages',
#     'league_history', 'leagues', 'nations', 'players.mysql',
#     'players_batting', 'players_fielding', 'players_career',
#     'players_contract', 'players_injury', 'players_pitching',
#     'players_roster_status', 'players_salary_history', 'players_value',
#     'team_affiliations', 'states', 'team_roster', 'teams.mysql',
#     'trade_history'
# ]

# proj_scripts = {
#     "offense": """INSERT OR IGNORE INTO players_batting_expected
#         (rating_id, PA, AB, H, "1B", "2B", "3B", HR, BB, HBP, K, AVG, OBP, SLG, wOBA)
#         VALUES (:rating_id, :PA, :AB, :H, :_1B, :_2B, :_3B, :HR, :BB, :HBP, :K, :AVG, :OBP, :SLG, :wOBA)""",
#     "basepath": """INSERT OR IGNORE INTO players_basepath_expected
#         (rating_id, SB, CS) VALUES (:rating_id, :SB, :CS)""",
#     "defense": """INSERT OR IGNORE INTO players_fielding_expected
#         (rating_id, C, "1B", "2B", "3B", SS, LF, CF, RF, DH)
#         VALUES (:rating_id, :C, :_1B, :_2B, :_3B, :SS, :LF, :CF, :RF, :DH)""",
#     "value": """INSERT OR IGNORE INTO players_run_value
#         (rating_id, batting_runs, basepath_runs, fielding_runs, total_runs, WAR)
#         VALUES (:rating_id, :wRAA, :BR_runs, :Def_runs, :Total_runs, :WAR)"""
# }


# ---- SQLite Utility Functions ----

# def get_db():
#     """Retrieve app DB connection, creating it if needed."""
#     if 'db' not in g:
#         g.db = sqlite3.connect(
#             current_app.config['DATABASE'],
#             detect_types=sqlite3.PARSE_DECLTYPES
#         )
#         g.db.row_factory = sqlite3.Row
#     return g.db


# def close_db(e=None):
#     """Close all open DB connections in the Flask app context."""
#     for key in ['db']:
#         con = g.pop(key, None)
#         if con is not None:
#             con.close()


# @click.command('init-db')
# def init_db_command():
#     """CLI: Initialize SQLite DB using schema.sql."""
#     db = get_db()
#     with current_app.open_resource(os.path.join('sql','schema.sql'), 'r') as f:
#         db.executescript(f.read())
#     click.echo('Initialized the SQLite database.')


# ---- Data Dump Utilities ----

# def check_new_heaps():
#     """Return list of new data dump folder paths (may be empty)."""
#     dump_path = current_app.config['DUMP_PATH']
#     return [os.path.join(dump_path, heap, "mysql") for heap in os.listdir(dump_path)]


# def fix_insert_ignore(sql: str) -> str:
#     """Convert MySQL's INSERT IGNORE to SQLite-compatible syntax."""
#     return re.sub(r'^insert\s+ignore', 'insert or ignore', sql, flags=re.IGNORECASE)


# def sql_dump_to_staging(db, filepath, commit_every=100):
#     """Load SQL dump file into staging DB."""
#     with open(filepath, 'r', encoding='utf-8') as f:
#         for i, line in enumerate(f, 1):
#             if line.startswith("#") or not line.strip():
#                 continue
#             sql = fix_insert_ignore(line) if line.lower().startswith("insert ignore") else line
#             db.executescript(sql)
#             if i % commit_every == 0:
#                 db.commit()
#         db.commit()

# ---- Migration + Projection ----

# def inject_db_path(template: str, db_path: str) -> str:
#     return template.replace("{{STAGGING_DB_PATH}}", db_path)


# def inject_heap_date(template: str, heap_date: list) -> str:
#     return template.replace("{{HEAP_DATE}}", f'{heap_date[1]}-{heap_date[2]}-1')

# def update_projection_batches(batches, projections=None, db=None, inject=False, final=False):
#     if final:
#         for key in batches:
#             if batches[key]:  # Only execute if not empty
#                 db.executemany(proj_scripts[key], batches[key])
#         db.commit()
#         return None

#     if projections:
#         for projection in projections:
#             for key in batches:
#                 value = projection.get(key)
#                 if value is not None:
#                     batches[key].append(value)

#     if inject:
#         for key in batches:
#             if batches[key]:  # Only execute if not empty
#                 db.executemany(proj_scripts[key], batches[key])
#         db.commit()
#         return {k: [] for k in batches}  # Reset batches
#     return batches

# def process_player(player):
#     try:
#         projector = BatterProjection(player)
#         result = projector.calc_expected_stats()
#         if result is None:
#             current_app.logger.warning(f"No result for player: {player.get('rating_id')}")
#         return result
#     except Exception as e:
#         current_app.logger.warning(f"Error processing player {player.get('rating_id')}: {e}")
#         return None

# @click.command('update-db')
# def update_db_command():
#     """CLI: Update SQLite DB with new data dump heaps."""
#     update_db()
#     click.echo('Updated the SQLite database.')


# def update_db():
#     logger = current_app.logger
#     heaps = check_new_heaps()
#     if not heaps:
#         logger.info("No new heaps found.")
#         return None
#     logger.info(f"Found {len(heaps)} new heap(s).")
#     db = get_db()

#     for heap_number, heap in enumerate(heaps, 1):
#         heap_date = Path(heap).parts[-2].split('_')
#         logger.info(f"[{heap_number}/{len(heaps)}] Processing heap: {heap_date[1]}_{heap_date[2]}")
#         staging_db = sqlite3.connect(
#             current_app.config["STAGGING"],
#             detect_types=sqlite3.PARSE_DECLTYPES
#         )
#         staging_db.row_factory = sqlite3.Row

#         try:
#             for filename in tqdm(os.listdir(heap), desc="Processing dump files"):
#                 if filename.startswith(tuple(DUMP_INCLUSION_LIST)):
#                     filepath = os.path.join(heap, filename)
#                     if os.path.isfile(filepath):
#                         sql_dump_to_staging(staging_db, filepath)
#             staging_db.commit()
#         finally:
#             staging_db.close()

#         logger.info("Starting migration")
#         with current_app.open_resource(os.path.join('sql','migration.sql'), 'r') as f:
#             sql_script = inject_db_path(f.read(), current_app.config["STAGGING"])
#             sql_script = inject_heap_date(sql_script, heap_date)
#             db.executescript(sql_script)

#         with current_app.open_resource(os.path.join('sql','get_projection_inputs.sql'), 'r') as f:
#             query = inject_heap_date(f.read(), heap_date)
#             cursor = db.execute(query)

#         players = [dict(row) for row in cursor.fetchall()]
#         cursor.close()
#         logger.info(f"Number of players: {len(players)}")
#         with Pool(processes=cpu_count()) as pool:
#             projections = list(tqdm(
#                 pool.imap_unordered(process_player, players),
#                 total=len(players),
#                 desc="Projecting players"
#             ))
#         projections = [p for p in projections if p is not None]
#         logger.info(f"Generated {len(projections)} projections (after filtering None)")
#         if len(projections) > 0:
#             logger.debug(f"First projection: {projections[0]}")
#         batches = {
#             "offense": [],
#             "basepath": [],
#             "defense": [],
#             "value": []
#         }
#         # Batch insert projections
#         batch_size = 1000
#         for i in range(0, len(projections), batch_size):
#             chunk = projections[i:i + batch_size]
#             batches = update_projection_batches(batches=batches, projections=chunk, inject=True, db=db)
#         update_projection_batches(batches=batches, db=db, final=True)
#     logger.info("Migration and projection complete!")
#     close_db()

# ---- Flask App Binding ----

# sqlite3.register_converter("timestamp", lambda v: datetime.fromisoformat(v.decode()))


# def init_app(app):
#     """Attach CLI commands and DB teardown to Flask app."""
#     app.teardown_appcontext(close_db)
#     app.cli.add_command(init_db_command)
#     app.cli.add_command(update_db_command)