import os
import pytest
from unittest.mock import MagicMock, patch
from app.db import staging as staging_module


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


def test_get_processed_heap_keys_returns_set_of_tuples_and_commits():
    # The commit() here isn't optional bookkeeping -- see the comment on
    # get_processed_heap_keys() in staging.py (docs/tickets/0007): without
    # it, this SELECT silently pins a stale transaction snapshot that later
    # collides with the staging DROP/CREATE and raises MySQL error 1412.
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_db.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [
        {"year": "2023", "month": "05"},
        {"year": "2023", "month": "yearly"},
    ]

    result = staging_module.get_processed_heap_keys(mock_db)

    assert result == {("2023", "05"), ("2023", "yearly")}
    mock_cursor.execute.assert_called_once_with("SELECT year, month FROM processed_heaps")
    mock_db.commit.assert_called_once()


@patch("app.db.staging.get_db")
@patch("app.db.staging.get_processed_heap_keys")
def test_check_new_heaps_returns_sorted_unprocessed_heaps(
    mock_processed, mock_get_db, monkeypatch, app
):
    monkeypatch.setattr(
        "os.listdir",
        lambda path: [
            "heap_2023_5", "heap_2022_10", "heap_invalid",
            "heap_2023_x", "heap_2023_1", "heap_2021_yearly",
        ],
    )
    mock_processed.return_value = set()
    fake_path = "/fake/dump/path"

    with app.app_context():
        staging_module.current_app.config["DUMP_PATH"] = fake_path
        result = staging_module.check_new_heaps()

    # Sorted by (year, month), yearly pinned to month 13 so it always sorts
    # after that year's monthlies -- but 2021 as a whole still sorts before
    # 2022/2023's monthlies.
    assert result == [
        (os.path.join(fake_path, "heap_2021_yearly", "mysql"), False),
        (os.path.join(fake_path, "heap_2022_10", "mysql"), True),
        (os.path.join(fake_path, "heap_2023_1", "mysql"), True),
        (os.path.join(fake_path, "heap_2023_5", "mysql"), True),
    ]


@patch("app.db.staging.get_db")
@patch("app.db.staging.get_processed_heap_keys")
def test_check_new_heaps_filters_out_already_processed(
    mock_processed, mock_get_db, monkeypatch, app
):
    monkeypatch.setattr(
        "os.listdir",
        lambda path: ["heap_2023_5", "heap_2022_10", "heap_2021_yearly"],
    )
    # (year, month) keys as recorded in processed_heaps -- month is the raw
    # directory-name segment ("10", "yearly"), matching what check_new_heaps()
    # itself parses. See docs/tickets/0007.
    mock_processed.return_value = {("2022", "10"), ("2021", "yearly")}
    fake_path = "/fake/dump/path"

    with app.app_context():
        staging_module.current_app.config["DUMP_PATH"] = fake_path
        result = staging_module.check_new_heaps()

    assert result == [(os.path.join(fake_path, "heap_2023_5", "mysql"), True)]


@pytest.mark.parametrize("input_sql, expected_sql", [
    # clean_mysql_dump only strips '#'-comment lines today -- it does not
    # rewrite INSERT IGNORE (that was SQLite-era behavior, removed).
    ("insert ignore into table values(1)", "insert ignore into table values(1)"),
    ("INSERT IGNORE something", "INSERT IGNORE something"),
    ("InSeRt IgNoRe whatever", "InSeRt IgNoRe whatever"),
    ("insert into table values(1)", "insert into table values(1)"),
    ("# comment line", ""),
])
def test_clean_mysql_dump(input_sql, expected_sql):
    result = staging_module.clean_mysql_dump(input_sql)
    assert result.strip() == expected_sql.strip()


def test_sql_dump_to_staging_executes_statements_and_commits(tmp_path):
    sql_lines = [
        "# comment line\n",
        "insert ignore into table values(1);\n",
        "insert into table values(2);\n",
        "insert ignore into table values(3);\n",
    ]
    file_path = tmp_path / "dump.sql"
    file_path.write_text("".join(sql_lines))

    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_db.cursor.return_value.__enter__.return_value = mock_cursor

    staging_module.sql_dump_to_staging(mock_db, str(file_path))

    executed = [c.args[0] for c in mock_cursor.execute.call_args_list]
    assert executed == [
        "insert ignore into table values(1);",
        "insert into table values(2);",
        "insert ignore into table values(3);",
    ]
    mock_db.commit.assert_called_once()


def test_sql_dump_to_staging_missing_file_logs_and_returns(tmp_path):
    mock_db = MagicMock()
    missing_path = str(tmp_path / "does_not_exist.sql")

    staging_module.sql_dump_to_staging(mock_db, missing_path)

    mock_db.cursor.assert_not_called()
    mock_db.commit.assert_not_called()


@patch("app.db.staging.sql_dump_to_staging")
def test_load_sql_dumps_into_staging_only_loads_included_files(
    mock_dump, monkeypatch
):
    monkeypatch.setattr(
        "os.listdir", lambda path: ["players.mysql.sql", "teams.mysql.sql", "ignore.sql"]
    )
    monkeypatch.setattr("os.path.isfile", lambda path: True)
    mock_db = MagicMock()

    with patch(
        "app.db.staging.DUMP_INCLUSION_LIST", ["players.mysql", "teams.mysql"]
    ):
        staging_module.load_sql_dumps_into_staging(mock_db, "/dummy/path")

    assert mock_dump.call_count == 2
