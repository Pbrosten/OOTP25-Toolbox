import os
import pytest
from unittest.mock import MagicMock, patch
from app.db import staging as staging_module

@pytest.fixture
def app_config(monkeypatch):
    monkeypatch.setattr("flask.current_app", MagicMock())
    yield


@patch("app.db.staging.pymysql.connect")
def test_connect_staging_db_resets_tables(mock_connect, app):
    """connect_staging_db() must reset staging before each load -- see
    docs/tickets/0013. Without this, a dump file that doesn't self-reset its
    own table silently accumulates cross-heap data."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [("players",), ("teams",)]
    mock_connect.return_value = mock_conn

    with app.app_context():
        staging_module.current_app.config.update(
            {"DB_HOST": "host", "DB_USER": "user", "DB_PASSWORD": "pw", "DB_PORT": "3306"}
        )
        result = staging_module.connect_staging_db()

    assert result is mock_conn
    executed = [c.args[0] for c in mock_cursor.execute.call_args_list]
    assert executed[0] == "SET FOREIGN_KEY_CHECKS=0;"
    assert executed[1] == "SHOW TABLES;"
    assert "DROP TABLE IF EXISTS `players`;" in executed
    assert "DROP TABLE IF EXISTS `teams`;" in executed
    assert executed[-1] == "SET FOREIGN_KEY_CHECKS=1;"

def test_check_new_heaps(monkeypatch, app):
    monkeypatch.setattr('os.listdir', lambda path: [
        "heap_2023_5", "heap_2022_10", "heap_invalid", "heap_2023_x", "heap_2023_1", "heap_2021_yearly"
    ])

    fake_path = "/fake/dump/path"

    with app.app_context():
        # Set DUMP_PATH inside the Flask app config
        staging_module.current_app.config["DUMP_PATH"] = fake_path

        short_expected = [
            os.path.join(fake_path, "heap_2022_10", "mysql"),
            os.path.join(fake_path, "heap_2023_1", "mysql"),
            os.path.join(fake_path, "heap_2023_5", "mysql"),
        ]
        long_expected = [
            os.path.join(fake_path, "heap_2021_yearly", "mysql")
        ]

        short_heaps, long_heaps = staging_module.check_new_heaps()

        assert short_heaps == short_expected
        assert long_heaps == long_expected

@pytest.mark.parametrize("input_sql, expected_sql", [
    ("insert ignore into table values(1)", "INSERT OR IGNORE into table values(1)"),
    ("INSERT IGNORE something", "INSERT IGNORE something"),  # No change expected
    ("InSeRt IgNoRe whatever", "InSeRt IgNoRe whatever"),    # No change expected
    ("insert into table values(1)", "insert into table values(1)"),
    ("# comment line", ""),
])
def test_clean_mysql_dump(input_sql, expected_sql):
    result = staging_module.clean_mysql_dump(input_sql)
    assert result.strip() == expected_sql.strip()

def test_sql_dump_to_staging(tmp_path):
    sql_lines = [
        "# comment line\n",
        "insert ignore into table values(1);\n",
        "insert into table values(2);\n",
        "insert ignore into table values(3);\n"
    ]
    file_path = tmp_path / "dump.sql"
    file_path.write_text("".join(sql_lines))

    class MockDB:
        def __init__(self):
            self.executed = []
            self.commit_called = False

        def executescript(self, sql):
            self.executed.append(sql.strip())

        def commit(self):
            self.commit_called = True

    db = MockDB()

    # Run the function
    staging_module.sql_dump_to_staging(db, str(file_path))

    # Expected cleaned SQL
    expected_sql = "\n".join([
        "INSERT OR IGNORE into table values(1);",
        "insert into table values(2);",
        "INSERT OR IGNORE into table values(3);"
    ])

    assert db.executed == [expected_sql.strip()]
    assert db.commit_called is True
