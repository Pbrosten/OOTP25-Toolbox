import os
import pytest
from unittest.mock import MagicMock, patch
from app.db import stagging as stagging_module

@pytest.fixture
def app_config(monkeypatch):
    monkeypatch.setattr("flask.current_app", MagicMock())
    yield

def test_check_new_heaps(app, monkeypatch):
    monkeypatch.setattr('os.listdir', lambda path: [
        "heap_2023_5", "heap_2022_10", "heap_invalid", "heap_2023_x", "heap_2023_1"
    ])

    expected_sorted = [
        os.path.join("/fake/dump/path", "heap_2022_10", "mysql"),
        os.path.join("/fake/dump/path", "heap_2023_1", "mysql"),
        os.path.join("/fake/dump/path", "heap_2023_5", "mysql"),
    ]

    result = stagging_module.check_new_heaps()
    assert result == expected_sorted

@pytest.mark.parametrize("input_sql, expected_sql", [
    ("insert ignore into table values(1)", "insert or ignore into table values(1)"),
    ("INSERT IGNORE something", "insert or ignore something"),
    ("InSeRt IgNoRe whatever", "insert or ignore whatever"),
    ("insert into table values(1)", "insert into table values(1)"),
    ("-- insert ignore", "-- insert ignore"),
])
def test_fix_insert_ignore(input_sql, expected_sql):
    result = stagging_module.fix_insert_ignore(input_sql)
    assert result == expected_sql

def test_sql_dump_to_staging(tmp_path):
    sql_lines = [
        "# comment line\n",
        "\n",
        "insert ignore into table values(1);\n",
        "insert into table values(2);\n",
        "insert ignore into table values(3);\n"
    ]
    file_path = tmp_path / "dump.sql"
    file_path.write_text("".join(sql_lines))

    class MockDB:
        def __init__(self):
            self.executed = []
            self.commit_count = 0

        def executescript(self, sql):
            self.executed.append(sql.strip())

        def commit(self):
            self.commit_count += 1

    db = MockDB()

    # Run function with commit_every=2 to test multiple commits
    stagging_module.sql_dump_to_staging(db, str(file_path), commit_every=2)

    # Check executed sql (insert ignore fixed)
    expected_sqls = [
        "insert or ignore into table values(1);",
        "insert into table values(2);",
        "insert or ignore into table values(3);"
    ]
    assert db.executed == expected_sqls

    # Check commit called correct number of times
    assert db.commit_count == 2
