import sqlite3
import logging
from datetime import datetime
from flask import current_app, g
import pymysql
from pymysql.cursors import DictCursor

logger = logging.getLogger("app.db.connection")


def get_db():
    if "db" not in g:
        cfg = current_app.config
        if cfg.get("DB_HOST") and pymysql is not None:
            logger.info("Found MariaDB")
            g.db = pymysql.connect(
                host=cfg.get("DB_HOST"),
                user=cfg.get("DB_USER"),
                password=cfg.get("DB_PASSWORD"),
                db=cfg.get("DB_NAME"),
                port=int(cfg.get("DB_PORT", 3306)),
                cursorclass=DictCursor,
                charset="utf8mb4",
                autocommit=False,
            )  # type: ignore
        else:
            logger.info("defaulting to SQLite")
            g.db = sqlite3.connect(
                cfg["DATABASE"], detect_types=sqlite3.PARSE_DECLTYPES
            )
            g.db.row_factory = sqlite3.Row

    return g.db


def close_db(e=None):
    con = g.pop("db", None)
    if con is not None:
        con.close()


def register_converters():
    sqlite3.register_converter(
        "timestamp", lambda v: datetime.fromisoformat(v.decode())
    )
