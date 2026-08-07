import os
import pytest

from unittest.mock import MagicMock, patch

from app.db import update as update_module

def test_extract_heap_date_from_path():
    path = "/some/path/dump_2023_08/mysql"
    assert update_module.extract_heap_date_from_path(path) == ['dump', '2023', '08']


def test_run_migration_short_executes_statements_and_returns_rows_affected(app):
    sql_content = "INSERT INTO a VALUES (1); INSERT INTO b VALUES (2);"
    mock_file = MagicMock()
    mock_file.read.return_value = sql_content

    mock_cursor = MagicMock()
    mock_cursor.rowcount = 3
    db = MagicMock()
    db.cursor.return_value.__enter__.return_value = mock_cursor

    with app.app_context():
        with patch("app.db.update.current_app.open_resource") as mock_open:
            mock_open.return_value.__enter__.return_value = mock_file
            rows_affected = update_module.run_migration_short(["dump", "2023", "08"], db)

    expected_path = os.path.join("db", "sql_scripts", "migration", "migration_short.sql")
    mock_open.assert_called_once_with(expected_path, "r")
    executed = [c.args[0] for c in mock_cursor.execute.call_args_list]
    assert executed == ["INSERT INTO a VALUES (1)", "INSERT INTO b VALUES (2)"]
    db.commit.assert_called_once()
    db.rollback.assert_not_called()
    assert rows_affected == 6  # rowcount=3, summed across 2 statements


def test_run_migration_short_rolls_back_and_reraises_on_error(app):
    sql_content = "INSERT INTO a VALUES (1);"
    mock_file = MagicMock()
    mock_file.read.return_value = sql_content

    mock_cursor = MagicMock()
    mock_cursor.execute.side_effect = Exception("boom")
    db = MagicMock()
    db.cursor.return_value.__enter__.return_value = mock_cursor

    with app.app_context():
        with patch("app.db.update.current_app.open_resource") as mock_open:
            mock_open.return_value.__enter__.return_value = mock_file
            with pytest.raises(Exception, match="boom"):
                update_module.run_migration_short(["dump", "2023", "08"], db)

    db.rollback.assert_called_once()
    db.commit.assert_not_called()


def test_run_migration_long_executes_statements_and_returns_rows_affected(app):
    sql_content = "INSERT INTO a VALUES (1); INSERT INTO b VALUES (2);"
    mock_file = MagicMock()
    mock_file.read.return_value = sql_content

    mock_cursor = MagicMock()
    mock_cursor.rowcount = 2
    db = MagicMock()
    db.cursor.return_value.__enter__.return_value = mock_cursor

    with app.app_context():
        with patch("app.db.update.current_app.open_resource") as mock_open:
            mock_open.return_value.__enter__.return_value = mock_file
            rows_affected = update_module.run_migration_long(["dump", "2023", "08"], db)

    expected_path = os.path.join("db", "sql_scripts", "migration", "migration_long.sql")
    mock_open.assert_called_once_with(expected_path, "r")
    assert mock_cursor.execute.call_count == 2
    db.commit.assert_called_once()
    assert rows_affected == 4  # rowcount=2, summed across 2 statements


def test_run_migration_long_rolls_back_and_reraises_on_error(app):
    sql_content = "INSERT INTO a VALUES (1);"
    mock_file = MagicMock()
    mock_file.read.return_value = sql_content

    mock_cursor = MagicMock()
    mock_cursor.execute.side_effect = Exception("boom")
    db = MagicMock()
    db.cursor.return_value.__enter__.return_value = mock_cursor

    with app.app_context():
        with patch("app.db.update.current_app.open_resource") as mock_open:
            mock_open.return_value.__enter__.return_value = mock_file
            with pytest.raises(Exception, match="boom"):
                update_module.run_migration_long(["dump", "2023", "08"], db)

    db.rollback.assert_called_once()
    db.commit.assert_not_called()


def test_fetch_projection_inputs_returns_rows_as_dicts(app):
    sql_content = "SELECT * FROM players;"
    mock_file = MagicMock()
    mock_file.read.return_value = sql_content

    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [{"id": 1}, {"id": 2}]
    db = MagicMock()
    db.cursor.return_value.__enter__.return_value = mock_cursor

    with app.app_context():
        with patch("app.db.update.current_app.open_resource") as mock_open:
            mock_open.return_value.__enter__.return_value = mock_file
            result = update_module.fetch_projection_inputs(["dump", "2023", "08"], db)

    expected_path = os.path.join("db", "sql_scripts", "migration", "get_projection_inputs.sql")
    mock_open.assert_called_once_with(expected_path, "r")
    mock_cursor.execute.assert_called_once_with("SELECT * FROM players")
    db.commit.assert_called_once()
    assert result == [{"id": 1}, {"id": 2}]


@patch("app.db.update.process_player", side_effect=lambda p: {"id": p["id"], "value": 42})
@patch("app.db.update.cpu_count", return_value=1)
@patch("app.db.update.Pool")
def test_project_players(mock_pool_cls, mock_cpu, mock_proc):
    mock_pool = mock_pool_cls.return_value.__enter__.return_value
    mock_pool.imap_unordered.return_value = ({"id": i, "value": 42} for i in range(10))

    players = [{"id": i} for i in range(10)]
    results = update_module.project_players(players)

    assert len(results) == 10
    assert all("value" in r for r in results)


@patch("app.db.update.update_projection_batches")
def test_insert_projections(mock_update):
    # update_projection_batches returns (batches_or_None, rows_written) when
    # inject/final -- see docs/tickets/0016.
    mock_update.return_value = (
        {"offense": [], "basepath": [], "defense": [], "value": []},
        10,
    )
    db = MagicMock()
    projections = [{"id": i} for i in range(2500)]
    rows_inserted = update_module.insert_projections(projections, db, batch_size=1000)

    # 3 calls: 2 for chunks, 1 final
    assert mock_update.call_count == 4
    # First call with projections
    assert mock_update.call_args_list[0][1]['inject'] is True
    # Last call with final=True
    assert mock_update.call_args_list[-1][1]['final'] is True
    assert rows_inserted == 40


@patch("app.db.update.mark_heap_processed")
@patch("app.db.update.insert_projections", return_value=7)
@patch("app.db.update.project_players", return_value=[{"id": 1}, {"id": 2}])
@patch("app.db.update.fetch_projection_inputs", return_value=[{"id": 1}, {"id": 2}])
@patch("app.db.update.run_migration_short", return_value=42)
@patch("app.db.update.load_sql_dumps_into_staging")
@patch("app.db.update.connect_staging_db")
@patch("app.db.update.extract_heap_date_from_path", return_value=["dump", "2023", "08"])
def test_process_single_heap_short(
    mock_extract, mock_connect, mock_load, mock_migration_short,
    mock_fetch, mock_project, mock_insert, mock_mark_processed,
):
    mock_staging_db = MagicMock()
    mock_connect.return_value = mock_staging_db
    db = MagicMock()

    counts = update_module.process_single_heap(
        "/dummy/heap_path", 1, 10, db, short_heap=True
    )

    mock_connect.assert_called_once()
    mock_load.assert_called_once_with(mock_staging_db, "/dummy/heap_path")
    mock_staging_db.close.assert_called_once()

    mock_migration_short.assert_called_once_with(["dump", "2023", "08"], db)
    mock_fetch.assert_called_once_with(["dump", "2023", "08"], db)
    mock_project.assert_called_once_with([{"id": 1}, {"id": 2}])
    mock_insert.assert_called_once_with([{"id": 1}, {"id": 2}], db)
    mock_mark_processed.assert_called_once_with(db, ["dump", "2023", "08"], True)

    assert counts == {"ratings_inserted": 42, "players_updated": 0, "projections_inserted": 7}


@patch("app.db.update.mark_heap_processed")
@patch("app.db.update.update_player_age", return_value=5)
@patch("app.db.update.run_migration_long", return_value=10)
@patch("app.db.update.load_sql_dumps_into_staging")
@patch("app.db.update.connect_staging_db")
@patch("app.db.update.extract_heap_date_from_path", return_value=["dump", "2023", "08"])
def test_process_single_heap_long(
    mock_extract, mock_connect, mock_load, mock_migration_long,
    mock_update_age, mock_mark_processed,
):
    mock_staging_db = MagicMock()
    mock_connect.return_value = mock_staging_db
    db = MagicMock()

    counts = update_module.process_single_heap(
        "/dummy/heap_path", 1, 10, db, short_heap=False
    )

    mock_connect.assert_called_once()
    mock_load.assert_called_once_with(mock_staging_db, "/dummy/heap_path")
    mock_staging_db.close.assert_called_once()

    mock_migration_long.assert_called_once_with(["dump", "2023", "08"], db)
    mock_update_age.assert_called_once_with(db=db, heap_date=["dump", "2023", "08"])
    mock_mark_processed.assert_called_once_with(db, ["dump", "2023", "08"], False)

    assert counts == {"ratings_inserted": 0, "players_updated": 15, "projections_inserted": 0}
