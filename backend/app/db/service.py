import os

from flask import current_app

from .connection import get_db, close_db
from .staging import check_new_heaps
from .update import process_single_heap

# Guards update_database() itself (not just the API's job-runner path), so a
# CLI run and an API-triggered job -- or two CLI runs -- can't load into the
# same staging schema concurrently. Uses a MariaDB named lock (GET_LOCK)
# rather than a threading.Lock: the CLI runs as its own OS process, separate
# from the always-on API server process, so an in-process lock wouldn't be
# visible to it at all -- GET_LOCK is scoped to the DB server, so every
# process talking to the same MariaDB instance shares it. See docs/tickets/0010.
_UPDATE_LOCK_NAME = "ootp_toolbox_update_db"


class UpdateAlreadyRunningError(Exception):
    """Raised when update_database() is called while another run, from any
    entry point, is already in progress."""


def init_database() -> dict:
    """Create the database schema from schema.sql."""
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
            cursor.close()
            conn.commit()
        finally:
            close_db()

    return {"status": "ok"}


def update_database() -> dict:
    """Ingest any new dump heaps and run the migration/projection pipeline.

    Raises UpdateAlreadyRunningError if another update is already in
    progress, from this or any other entry point (CLI or API).
    """
    app = current_app._get_current_object()
    with app.app_context():
        logger = current_app.logger
        conn = get_db()
        acquired = False
        try:
            with conn.cursor() as cur:
                cur.execute(f"SELECT GET_LOCK('{_UPDATE_LOCK_NAME}', 0) AS locked")
                acquired = bool(cur.fetchone()["locked"])
            if not acquired:
                raise UpdateAlreadyRunningError("update already in progress")

            sorted_heaps = check_new_heaps()
            if not sorted_heaps:
                logger.info("No new heaps found.")
                return {"status": "ok", "heaps_processed": 0, "long_heaps": 0, "short_heaps": 0}

            logger.info(sorted_heaps)
            total_heaps = len(sorted_heaps)
            count_short = sum(1 for _, is_short in sorted_heaps if is_short)
            count_long = total_heaps - count_short

            logger.info(
                f"Found {count_long} new long heap(s) and {count_short} new short heap(s)."
            )

            logger.info("Migrating heaps in order")
            for heap_number, (heap_path, short_heap_flag) in enumerate(sorted_heaps, 1):
                process_single_heap(
                    heap_path, heap_number, total_heaps, conn, short_heap=short_heap_flag
                )

            conn.commit()
            logger.info("Migration and projection complete!")

            return {
                "status": "ok",
                "heaps_processed": total_heaps,
                "long_heaps": count_long,
                "short_heaps": count_short,
            }
        finally:
            if acquired:
                with conn.cursor() as cur:
                    cur.execute(f"SELECT RELEASE_LOCK('{_UPDATE_LOCK_NAME}')")
            close_db()
