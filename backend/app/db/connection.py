import sqlite3
import logging
from datetime import datetime
from flask import current_app, g
import pymysql
from pymysql.cursors import DictCursor

logger = logging.getLogger("app.db.connection")


def get_db() -> pymysql.connections.Connection:
    if "db" not in g:
        cfg = current_app.config

        host = cfg.get("DB_HOST")
        if not host:
            logger.error("Missing database host in configuration!")
            raise RuntimeError("Database host not configured")

        g.db = pymysql.connect(
            host=host,
            user=cfg.get("DB_USER"),
            password=cfg.get("DB_PASSWORD"),
            db=cfg.get("DB_NAME"),
            port=int(cfg.get("DB_PORT", 3306)),
            cursorclass=DictCursor,
            charset="utf8mb4",
            autocommit=False,
        )

    return g.db


def close_db(e=None):
    con = g.pop("db", None)
    if con is not None:
        con.close()


def register_converters():
    sqlite3.register_converter(
        "timestamp", lambda v: datetime.fromisoformat(v.decode())
    )
