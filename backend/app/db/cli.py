import os
import click

from flask import current_app

from .connection import get_db, close_db
from .stagging import check_new_heaps
from .update import process_single_heap


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
    short_heaps, long_heaps = check_new_heaps()
    if not short_heaps and not long_heaps:
        logger.info("No new heaps found.")
        return

    logger.info(f"Found {len(short_heaps)} new short heap(s) and {len(long_heaps)} new long heap(s).")
    db = get_db()
    logger.info("Migrating long heaps")
    for heap_number, heap in enumerate(long_heaps, 1):
        process_single_heap(heap, heap_number, len(short_heaps), db, logger, short_heap=False)
    logger.info("Migrating short heaps")
    for heap_number, heap in enumerate(short_heaps, 1):
        process_single_heap(heap, heap_number, len(short_heaps), db, logger, short_heap=True)
    logger.info("Migration and projection complete!")
    close_db()