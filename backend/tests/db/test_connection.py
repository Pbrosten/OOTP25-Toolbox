from unittest.mock import MagicMock, patch

import pytest
from flask import g

from app.db import connection as conn_module


@patch("app.db.connection.pymysql.connect")
def test_get_db_creates_and_caches_connection(mock_connect, app):
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn

    with app.app_context():
        app.config.update(
            DB_HOST="host", DB_USER="user", DB_PASSWORD="pw",
            DB_NAME="ootp", DB_PORT="3306",
        )
        con = conn_module.get_db()

        assert con is mock_conn
        assert g.db is con
        mock_connect.assert_called_once_with(
            host="host",
            user="user",
            password="pw",
            db="ootp",
            port=3306,
            cursorclass=conn_module.DictCursor,
            charset="utf8mb4",
            autocommit=False,
        )

        # Subsequent calls in the same app context reuse the cached connection.
        con2 = conn_module.get_db()
        assert con2 is con
        mock_connect.assert_called_once()


def test_get_db_raises_without_db_host(app):
    with app.app_context():
        app.config["DB_HOST"] = None
        with pytest.raises(RuntimeError, match="Database host not configured"):
            conn_module.get_db()


@patch("app.db.connection.pymysql.connect")
def test_close_db_closes_and_clears_connection(mock_connect, app):
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn

    with app.app_context():
        app.config.update(DB_HOST="host", DB_USER="user", DB_PASSWORD="pw", DB_NAME="ootp")
        conn_module.get_db()
        assert "db" in g

        conn_module.close_db()

        assert "db" not in g
        mock_conn.close.assert_called_once()


def test_close_db_is_a_noop_without_a_connection(app):
    with app.app_context():
        conn_module.close_db()  # should not raise even if get_db() was never called
        assert "db" not in g
