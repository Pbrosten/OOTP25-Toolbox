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
    heaps = check_new_heaps()
    if not heaps:
        logger.info("No new heaps found.")
        return

    logger.info(f"Found {len(heaps)} new heap(s).")
    db = get_db()

    for heap_number, heap in enumerate(heaps, 1):
        process_single_heap(heap, heap_number, len(heaps), db, logger)

    logger.info("Migration and projection complete!")
    close_db()