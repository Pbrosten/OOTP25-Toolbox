import os
import click
from flask import current_app
from .connection import get_db, close_db
from .stagging import check_new_heaps, sql_dump_to_staging, DUMP_INCLUSION_LIST
from .migration import inject_db_path, inject_heap_date
from .projection import process_player, update_projection_batches

from pathlib import Path
from tqdm import tqdm
from multiprocessing import Pool, cpu_count
import sqlite3

@click.command('init-db')
def init_db_command():
    db = get_db()
    with current_app.open_resource(os.path.join('db','sql_scripts','schema.sql'), 'r') as f:
        db.executescript(f.read())
    click.echo('Initialized the SQLite database.')

@click.command('update-db')
def update_db_command():
    update_db()
    click.echo('Updated the SQLite database.')

def update_db():
    logger = current_app.logger
    heaps = check_new_heaps()
    if not heaps:
        logger.info("No new heaps found.")
        return

    logger.info(f"Found {len(heaps)} new heap(s).")
    db = get_db()

    for heap_number, heap in enumerate(heaps, 1):
        heap_date = Path(heap).parts[-2].split('_')
        logger.info(f"[{heap_number}/{len(heaps)}] Processing heap: {heap_date[1]}_{heap_date[2]}")
        staging_db = sqlite3.connect(
            current_app.config["STAGGING"],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        staging_db.row_factory = sqlite3.Row

        try:
            for filename in tqdm(os.listdir(heap), desc="Processing dump files"):
                if filename.startswith(tuple(DUMP_INCLUSION_LIST)):
                    filepath = os.path.join(heap, filename)
                    if os.path.isfile(filepath):
                        sql_dump_to_staging(staging_db, filepath)
            staging_db.commit()
        finally:
            staging_db.close()

        logger.info("Starting migration")
        with current_app.open_resource(os.path.join('sql','migration.sql'), 'r') as f:
            sql_script = inject_db_path(f.read(), current_app.config["STAGGING"])
            sql_script = inject_heap_date(sql_script, heap_date)
            db.executescript(sql_script)

        with current_app.open_resource(os.path.join('sql','get_projection_inputs.sql'), 'r') as f:
            query = inject_heap_date(f.read(), heap_date)
            cursor = db.execute(query)

        players = [dict(row) for row in cursor.fetchall()]
        cursor.close()
        logger.info(f"Number of players: {len(players)}")

        with Pool(processes=cpu_count()) as pool:
            projections = list(tqdm(
                pool.imap_unordered(process_player, players),
                total=len(players),
                desc="Projecting players"
            ))
        projections = [p for p in projections if p is not None]
        logger.info(f"Generated {len(projections)} projections (after filtering None)")
        if len(projections) > 0:
            logger.debug(f"First projection: {projections[0]}")

        batches = {
            "offense": [],
            "basepath": [],
            "defense": [],
            "value": []
        }
        batch_size = 1000
        for i in range(0, len(projections), batch_size):
            chunk = projections[i:i + batch_size]
            batches = update_projection_batches(batches=batches, projections=chunk, inject=True, db=db)
        update_projection_batches(batches=batches, db=db, final=True)

    logger.info("Migration and projection complete!")
    close_db()
