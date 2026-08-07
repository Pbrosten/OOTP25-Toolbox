import os
import re
import logging
import pymysql
from flask import current_app
from tqdm import tqdm

from .connection import get_db

DUMP_INCLUSION_LIST = [
    "players.mysql",
    "players_batting",
    "players_fielding",
    "players_pitching",
    "players_career_batting_stats",
    "teams.mysql",
]

# Regex to split SQL statements correctly, ignoring semicolons inside quotes
STATEMENT_RE = re.compile(r";\s*(?=(?:[^'\"`]*(['\"`])[^'\"`]*\1)*[^'\"`]*$)")

logger = logging.getLogger("app.db.staging")


def connect_staging_db():
    """Connect to the staging MariaDB and reset tables."""
    cfg = current_app.config
    conn = pymysql.connect(
        host=cfg["DB_HOST"],
        user=cfg["DB_USER"],
        password=cfg["DB_PASSWORD"],
        port=int(cfg.get("DB_PORT", 3306)),
        database="staging",
        autocommit=True,
        charset="utf8mb4",
    )

    with conn.cursor() as cur:
        logger.info("Dropping all existing tables in staging...")
        cur.execute("SET FOREIGN_KEY_CHECKS=0;")
        cur.execute("SHOW TABLES;")
        for (tbl,) in cur.fetchall():
            cur.execute(f"DROP TABLE IF EXISTS `{tbl}`;")
        cur.execute("SET FOREIGN_KEY_CHECKS=1;")
    logger.info("Staging DB reset complete.")
    return conn


def get_processed_heap_keys(db):
    """Return the set of (year, month) keys already recorded in processed_heaps."""
    with db.cursor() as cur:
        cur.execute("SELECT year, month FROM processed_heaps")
        keys = {(row["year"], row["month"]) for row in cur.fetchall()}
    # This SELECT is the first statement on `db`, so under autocommit=False it
    # silently opens a transaction and pins a REPEATABLE READ snapshot right
    # here. Without closing it out, that snapshot is still in effect when the
    # migration queries staging.* tables later -- which get DROP/CREATE'd by a
    # separate (autocommit=True) staging connection in between -- and InnoDB
    # raises 1412 "Table definition has changed" on the stale snapshot.
    db.commit()
    return keys


def check_new_heaps():
    """Return list of valid, not-yet-processed heap paths for processing."""
    dump_path = current_app.config["DUMP_PATH"]
    heaps = os.listdir(dump_path)
    valid_heaps = []

    for heap in heaps:
        parts = heap.split("_")
        if len(parts) < 3 or not parts[1].isdigit():
            continue

        year = parts[1]
        if parts[2] == "yearly":
            valid_heaps.append((heap, year, "yearly", 13, False))
        elif parts[2].isdigit():
            valid_heaps.append((heap, year, parts[2], int(parts[2]), True))

    sorted_heaps = sorted(valid_heaps, key=lambda x: (int(x[1]), x[3]))

    processed = get_processed_heap_keys(get_db())
    new_heaps = [h for h in sorted_heaps if (h[1], h[2]) not in processed]

    return [(os.path.join(dump_path, h[0], "mysql"), h[4]) for h in new_heaps]


def clean_mysql_dump(sql: str) -> str:
    """Remove comment lines and optionally modify SQL."""
    cleaned_lines = []
    for line in sql.splitlines():
        if line.strip().startswith("#"):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def sql_dump_to_staging(db, filepath: str):
    """
    Efficiently load a MySQL dump file into staging DB.

    - Streams large files to avoid memory issues.
    - Executes statements one by one safely.
    """
    if not os.path.exists(filepath):
        logger.error(f"Dump file not found: {filepath}")
        return

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            statement_buffer = ""
            with db.cursor() as cur:
                for line in f:
                    # Skip comments
                    if line.strip().startswith("#") or not line.strip():
                        continue
                    statement_buffer += line
                    if line.strip().endswith(";"):
                        stmt = statement_buffer.strip()
                        statement_buffer = ""
                        if stmt:
                            try:
                                cur.execute(stmt)
                            except pymysql.MySQLError as e:
                                logger.error(
                                    f"Error executing statement in {filepath}: {e}\n"
                                    f"Statement preview: {stmt[:200]}..."
                                )
                                raise
                # Execute any remaining statement
                if statement_buffer.strip():
                    cur.execute(statement_buffer.strip())
        db.commit()
    except Exception as e:
        logger.error(f"Failed to load dump: {e}")
        raise


def load_sql_dumps_into_staging(staging_db, heap_path, inclusion_list=None):
    inclusion_list = inclusion_list or DUMP_INCLUSION_LIST
    for filename in tqdm(os.listdir(heap_path), desc="Processing dump files"):
        if filename in inclusion_list or filename.startswith(tuple(inclusion_list)):
            filepath = os.path.join(heap_path, filename)
            if os.path.isfile(filepath):
                sql_dump_to_staging(staging_db, filepath)
