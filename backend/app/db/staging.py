import os
import re
import logging
import pymysql
from flask import current_app
from tqdm import tqdm

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


def check_new_heaps():
    """Return list of valid heap paths for processing."""
    dump_path = current_app.config["DUMP_PATH"]
    heaps = os.listdir(dump_path)
    valid_heaps = []

    for heap in heaps:
        parts = heap.split("_")
        if len(parts) < 3 or not parts[1].isdigit():
            continue

        year = int(parts[1])
        if parts[2] == "yearly":
            valid_heaps.append((heap, year, 13, False))
        elif parts[2].isdigit():
            valid_heaps.append((heap, year, int(parts[2]), True))

    sorted_heaps = sorted(valid_heaps, key=lambda x: (x[1], x[2]))
    return [(os.path.join(dump_path, h[0], "mysql"), h[3]) for h in sorted_heaps]


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

    logger.info(f"Loading dump: {filepath}")
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
        logger.info(f"Successfully loaded dump: {filepath}")
    except Exception as e:
        logger.error(f"Failed to load dump {filepath}: {e}")
        raise


def load_sql_dumps_into_staging(staging_db, heap_path, inclusion_list=None):
    inclusion_list = inclusion_list or DUMP_INCLUSION_LIST
    for filename in tqdm(os.listdir(heap_path), desc="Processing dump files"):
        if filename in inclusion_list or filename.startswith(tuple(inclusion_list)):
            filepath = os.path.join(heap_path, filename)
            if os.path.isfile(filepath):
                sql_dump_to_staging(staging_db, filepath)
