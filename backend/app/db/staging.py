import os
import re
import logging
import sqlite3
import pymysql
from flask import current_app

DUMP_INCLUSION_LIST = [
    # 'cities', 'continents', 'divisions', 'language_data', 'languages',
    # 'league_history', 'leagues', 'nations',
    "players.mysql",
    "players_batting",
    "players_fielding",
    # 'players_career',
    # 'players_contract', 'players_injury',
    "players_pitching",
    "players_career_batting_stats",
    # 'players_roster_status', 'players_salary_history', 'players_value',
    # 'team_affiliations', 'states', 'team_roster',
    "teams.mysql",
    # 'trade_history'
]

logger = logging.getLogger("app.db.staging")


def connect_staging_db():
    cfg = current_app.config
    host = cfg.get("DB_HOST")
    if not host:
        logger.error("Missing database host in configuration!")
        raise RuntimeError("Database host not configured")

    try:
        conn = pymysql.connect(
            host=host,
            user=cfg.get("DB_USER"),
            password=cfg.get("DB_PASSWORD"),
            port=int(cfg.get("DB_PORT", 3306)),
            autocommit=True,
            charset="utf8mb4",
        )
    except pymysql.MySQLError as e:
        logger.error(f"Failed to connect to MariaDB at {host}: {e}")
        raise

    with conn.cursor() as cur:
        cur.execute("DROP DATABASE IF EXISTS staging")
        cur.execute("CREATE DATABASE staging")
        cur.execute("USE staging")

    logger.info("Connected to fresh staging database.")
    return conn


def check_new_heaps():
    dump_path = current_app.config["DUMP_PATH"]
    heaps = os.listdir(dump_path)
    valid_heaps = []
    for heap in heaps:
        parts = heap.split("_")
        if len(parts) < 3:
            continue
        year_part = parts[1]
        if not year_part.isdigit():
            continue

        if parts[2] == "yearly":
            valid_heaps.append((heap, int(year_part), 13, False))
        elif parts[2].isdigit():
            valid_heaps.append((heap, int(year_part), int(parts[2]), True))

    sorted_heaps = sorted(valid_heaps, key=lambda x: (x[1], x[2]))

    result = [
        (os.path.join(dump_path, heap[0], "mysql"), heap[3]) for heap in sorted_heaps
    ]
    return result


def clean_mysql_dump(sql: str) -> str:
    cleaned_lines = []
    for line in sql.splitlines():
        if line.strip().startswith("#"):
            continue
        # Convert insert ignore → INSERT OR IGNORE
        line = line.replace("insert ignore", "INSERT OR IGNORE")
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def sql_dump_to_staging(db, filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        dump = clean_mysql_dump(f.read())

    try:
        db.executescript(dump)
        db.commit()
    except sqlite3.Error as e:
        print("SQLite Error during dump execution:", e)
        raise
