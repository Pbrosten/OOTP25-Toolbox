import sqlite3
import pytest

from flask import g
from datetime import datetime

from app.db import connection as conn_module

def test_get_db_creates_and_returns_connection(app):
    with app.app_context():
        con = conn_module.get_db()
        assert isinstance(con, sqlite3.Connection)
        assert 'db' in g
        assert g.db is con

        # Should return same connection on subsequent calls
        con2 = conn_module.get_db()
        assert con is con2


def test_close_db_closes_connection(app):
    with app.app_context():
        con = conn_module.get_db()
        assert 'db' in g

        conn_module.close_db()
        assert 'db' not in g

        # Connection should be closed
        with pytest.raises(sqlite3.ProgrammingError):
            con.execute("SELECT 1")

def test_register_converters_registers_timestamp():
    conn_module.register_converters()

    # Create an in-memory SQLite connection with detect_types to parse timestamp
    con = sqlite3.connect(":memory:", detect_types=sqlite3.PARSE_DECLTYPES)
    con.row_factory = sqlite3.Row

    # Create a table with a "timestamp" column (SQLite treats types flexibly)
    con.execute("CREATE TABLE test (event_time timestamp)")

    # Insert ISO 8601 string that should be converted to datetime by your converter
    dt_str = "2025-09-01T12:00:00"
    con.execute("INSERT INTO test (event_time) VALUES (?)", (dt_str,))

    # Select and verify that the value is returned as a datetime object (not string)
    row = con.execute("SELECT event_time FROM test").fetchone()
    event_time = row["event_time"]

    expected_dt = datetime.fromisoformat(dt_str)
    assert event_time == expected_dt
    assert isinstance(event_time, datetime)

    con.close()
