import os
import click

from flask import current_app

from .connection import get_db, close_db
from .staging import check_new_heaps
from .update import process_single_heap


@click.command("init-db")
def init_db_command():
    conn = get_db()
    try:
        cursor = conn.cursor()
        with current_app.open_resource(
            os.path.join("db", "sql_scripts", "schema-maria.sql"), "r", encoding="utf-8"
        ) as f:
            sql_script = f.read()
            for statement in sql_script.strip().split(";"):
                if statement.strip():
                    cursor.execute(statement)
        click.echo("Initialized the SQLite database.")
        cursor.close()
    finally:
        close_db()


@click.command("update-db")
def update_db_command():
    update_db()
    click.echo("Updated the SQLite database.")


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
    conn = get_db()
    try:
        logger.info("Migrating heaps in order")
        for heap_number, (heap_path, short_heap_flag) in enumerate(sorted_heaps, 1):
            process_single_heap(
                heap_path, heap_number, total_heaps, conn, short_heap=short_heap_flag
            )

        logger.info("Migration and projection complete!")
    finally:
        close_db()
