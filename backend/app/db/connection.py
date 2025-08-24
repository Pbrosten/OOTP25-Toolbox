import sqlite3
from datetime import datetime
from flask import current_app, g

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    con = g.pop('db', None)
    if con is not None:
        con.close()

def register_converters():
    sqlite3.register_converter("timestamp", lambda v: datetime.fromisoformat(v.decode()))
