import os
import sqlite3
from datetime import date

from pathlib import Path
from flask import current_app
from multiprocessing import Pool, cpu_count
from tqdm import tqdm

from .stagging import sql_dump_to_staging, DUMP_INCLUSION_LIST
from .migration import inject_db_path, inject_heap_date
from .projection import process_player, update_projection_batches

def process_single_heap(heap_path, heap_index, total_heaps, db, logger):
    heap_date = extract_heap_date_from_path(heap_path)
    logger.info(f"[{heap_index}/{total_heaps}] Processing heap: {heap_date[1]}_{heap_date[2]}")

    staging_db = connect_staging_db()
    try:
        load_sql_dumps_into_staging(staging_db, heap_path)
        staging_db.commit()
    finally:
        staging_db.close()

    run_migration_sql(heap_date, db)
    players = fetch_projection_inputs(heap_date, db)
    logger.info(f"Number of players: {len(players)}")

    projections = project_players(players)
    logger.info(f"Generated {len(projections)} projections (after filtering None)")

    if projections:
        logger.debug(f"First projection: {projections[0]}")

    insert_projections(projections, db)

    # Update age feature in db.players
    update_player_age(db=db, heap_date=heap_date)

def update_player_age(db, heap_date):
    current_date = date.fromisoformat(f"{heap_date[1]}-{heap_date[2]}-01")
    rows = db.execute("SELECT player_id, birth_date FROM players").fetchall()
    batch = []
    for player_id, birth_date in rows:
        if not birth_date:
            continue
        try:
            delta = current_date - birth_date
            age = round(delta.days / 365.25)

            batch.append((age, player_id))

            if len(batch) >= 500:
                db.executemany(
                    f"UPDATE players SET age = ? WHERE player_id = ?",
                    batch
                )
                db.commit()
                batch.clear()

        except ValueError:
            print(f"Skipping invalid birth_date format for player_id {player_id}: {birth_date}")

    if batch:
        db.executemany(
            f"UPDATE players SET age = ? WHERE player_id = ?",
            batch
        )
        db.commit()
    
def extract_heap_date_from_path(heap_path):
    # heap path should look like "{DUMP_PATH}/dump_yyyy_mm/mysql"
    return Path(heap_path).parts[-2].split('_')

def connect_staging_db():
    return sqlite3.connect(
        current_app.config["STAGGING"],
        detect_types=sqlite3.PARSE_DECLTYPES
    )

def load_sql_dumps_into_staging(staging_db, heap_path):
    for filename in tqdm(os.listdir(heap_path), desc="Processing dump files"):
        if filename.startswith(tuple(DUMP_INCLUSION_LIST)):
            filepath = os.path.join(heap_path, filename)
            if os.path.isfile(filepath):
                sql_dump_to_staging(staging_db, filepath)

def run_migration_sql(heap_date, db):
    with current_app.open_resource(os.path.join('db','sql_scripts','migration.sql'), 'r') as f:
        sql_script = inject_db_path(f.read(), current_app.config["STAGGING"])
        sql_script = inject_heap_date(sql_script, heap_date)
        db.executescript(sql_script)

def fetch_projection_inputs(heap_date, db):
    with current_app.open_resource(os.path.join('db', 'sql_scripts', 'get_projection_inputs.sql'), 'r') as f:
        query = inject_heap_date(f.read(), heap_date)
        cursor = db.execute(query)
    return [dict(row) for row in cursor.fetchall()]

def project_players(players):
    with Pool(processes=cpu_count()) as pool:
        results = list(tqdm(
            pool.imap_unordered(process_player, players),
            total=len(players),
            desc="Projecting players"
        ))
    return [r for r in results if r is not None]

def insert_projections(projections, db, batch_size=1000):
    batches = {key: [] for key in ("offense", "basepath", "defense", "value")}
    for i in range(0, len(projections), batch_size):
        chunk = projections[i:i + batch_size]
        batches = update_projection_batches(batches, projections=chunk, inject=True, db=db)
    update_projection_batches(batches, db=db, final=True)

