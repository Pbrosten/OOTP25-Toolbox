import os
import click
from pathlib import Path

from flask import current_app
from .connection import get_db, close_db
from .staging import check_new_heaps
from .update import process_single_heap
from app.player_similarity.similarity import compute_similarities


@click.command("init-db")
def init_db_command():
    """Initialize the database schema."""
    app = current_app._get_current_object()
    with app.app_context():
        conn = get_db()
        try:
            cursor = conn.cursor()
            with app.open_resource(
                os.path.join("db", "sql_scripts", "schema.sql"), "r", encoding="utf-8"
            ) as f:
                sql_script = f.read()
                for statement in sql_script.strip().split(";"):
                    if statement.strip():
                        cursor.execute(statement)
            click.echo("Initialized the database.")
            cursor.close()
            conn.commit()
        finally:
            close_db()


@click.command("update-db")
def update_db_command():
    """Run the database update process."""
    app = current_app._get_current_object()
    with app.app_context():
        update_db()
        click.echo("Updated the database.")


def update_db():
    logger = current_app.logger
    sorted_heaps = check_new_heaps()
    if not sorted_heaps:
        logger.info("No new heaps found.")
        return

    logger.info(sorted_heaps)
    total_heaps = len(sorted_heaps)
    count_short = sum(1 for _, is_short in sorted_heaps if is_short)
    count_long = total_heaps - count_short

    logger.info(
        f"Found {count_long} new long heap(s) and {count_short} new short heap(s)."
    )

    logger.info("Migrating heaps in order")
    latest_short_heap = ''
    for heap_number, (heap_path, short_heap_flag) in enumerate(sorted_heaps, 1):
        if short_heap_flag:
            latest_short_heap = heap_path
        process_single_heap(heap_path, heap_number, total_heaps, db, short_heap=short_heap_flag)
    latest_short_heap = f"{Path(latest_short_heap).parent.name.replace('dump_', '').replace('_', '-')}-1"
    logger.info("Migration and projection complete!")
    close_db()
    
    logger.info(f'Computing similaties as of {latest_short_heap}')
    compute_similarities(rating_date=latest_short_heap)
