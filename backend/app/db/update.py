import os
import logging
from datetime import date, datetime
from pathlib import Path
from multiprocessing import Pool, cpu_count

from tqdm import tqdm
from flask import current_app

from .staging import (
    load_sql_dumps_into_staging,
    connect_staging_db,
    DUMP_INCLUSION_LIST,
)
from .migration import inject_heap_date
from .projection import process_player, update_projection_batches

logger = logging.getLogger("api/db/update")


def process_single_heap(heap_path, heap_index, total_heaps, db, short_heap=True):
    heap_date = extract_heap_date_from_path(heap_path)
    logger.info(
        f"[{heap_index}/{total_heaps}] Processing {'short' if short_heap else 'long'} heap: {heap_date[1]}_{heap_date[2]}"
    )

    # Connect and reset staging
    staging_db = connect_staging_db()
    try:
        load_sql_dumps_into_staging(staging_db, heap_path)
    finally:
        staging_db.close()

    if short_heap:
        run_migration_short(heap_date, db)
        players = fetch_projection_inputs(heap_date, db)
        logger.info(f"Number of players: {len(players)}")

        projections = project_players(players)
        logger.info(f"Generated {len(projections)} projections (after filtering None)")

        if projections:
            logger.debug(f"First projection: {projections[0]}")

        insert_projections(projections, db)
        update_player_age(db=db, heap_date=heap_date)
    else:
        run_migration_long(heap_date, db)


def update_player_age(db, heap_date):
    """
    Update the 'age' field of all players based on their birth_date and the heap_date.

    Args:
        db: MariaDB connection object
        heap_date: tuple or list like (year, month, day) or (something, year, month)
    """
    current_date = date.fromisoformat(f"{heap_date[1]}-{heap_date[2]}-01")

    with db.cursor() as cursor:
        cursor.execute("SELECT player_id, birth_date FROM players")
        rows = cursor.fetchall()

        batch = []
        for player_id, birth_date in rows:
            if not birth_date:
                continue
            try:
                if isinstance(birth_date, str):
                    birth_date_obj = datetime.strptime(birth_date, "%Y-%m-%d").date()
                else:
                    birth_date_obj = birth_date
                delta = current_date - birth_date_obj
                age = round(delta.days / 365.25)
                batch.append((age, player_id))

                if len(batch) >= 500:
                    cursor.executemany(
                        "UPDATE players SET age = %s WHERE player_id = %s", batch
                    )
                    db.commit()
                    batch.clear()
            except ValueError:
                logger.warning(
                    f"Skipping invalid birth_date for player_id {player_id}: {birth_date}"
                )

        if batch:
            cursor.executemany(
                "UPDATE players SET age = %s WHERE player_id = %s", batch
            )
            db.commit()


def extract_heap_date_from_path(heap_path):
    # Expects "{DUMP_PATH}/dump_yyyy_mm/mysql"
    return Path(heap_path).parts[-2].split("_")


def run_migration_short(heap_date, db):
    script_path = os.path.join(
        "db", "sql_scripts", "migration", "migration_short-maria.sql"
    )
    with current_app.open_resource(script_path, "r") as f:
        sql_script = f.read()
        sql_script = inject_heap_date(sql_script, heap_date)

    with db.cursor() as cursor:
        try:
            for statement in sql_script.strip().split(";"):
                statement = statement.strip()
                if statement:
                    cursor.execute(statement)
        except Exception as e:
            db.rollback()
            logger.error(f"Migration failed: {e}")
            raise
        else:
            db.commit()


def run_migration_long(heap_date, db):
    script_path = os.path.join(
        "db", "sql_scripts", "migration", "migration_long-maria.sql"
    )
    with current_app.open_resource(script_path, "r") as f:
        sql_script = f.read()

    with db.cursor() as cursor:
        try:
            for statement in sql_script.strip().split(";"):
                statement = statement.strip()
                if statement:
                    cursor.execute(statement)
        except Exception as e:
            db.rollback()
            logger.error(f"Migration failed: {e}")
            raise
        else:
            db.commit()


def fetch_projection_inputs(heap_date, db):
    query_path = os.path.join(
        "db", "sql_scripts", "migration", "get_projection_inputs.sql"
    )
    with current_app.open_resource(query_path, "r") as f:
        sql_script = f.read()
        sql_script = inject_heap_date(sql_script, heap_date)

    with db.cursor() as cursor:
        try:
            for statement in sql_script.strip().split(";"):
                statement = statement.strip()
                if statement:
                    cursor.execute(statement)
        except Exception as e:
            db.rollback()
            logger.error(f"Migration failed: {e}")
            raise
        else:
            db.commit()
    return [dict(row) for row in cursor.fetchall()]


def project_players(players):
    with Pool(processes=cpu_count()) as pool:
        results = list(
            tqdm(
                pool.imap_unordered(process_player, players),
                total=len(players),
                desc="Projecting players",
            )
        )
    return [r for r in results if r is not None]


def insert_projections(projections, db, batch_size=1000):
    batches = {key: [] for key in ("offense", "basepath", "defense", "value")}
    for i in range(0, len(projections), batch_size):
        chunk = projections[i : i + batch_size]
        batches = update_projection_batches(
            batches, projections=chunk, inject=True, db=db
        )
    update_projection_batches(batches, db=db, final=True)
