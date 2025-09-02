import os
import pytest

from unittest.mock import MagicMock, patch

from app.db import update as update_module

def test_extract_heap_date_from_path():
    path = "/some/path/dump_2023_08/mysql"
    assert update_module.extract_heap_date_from_path(path) == ['dump', '2023', '08']


@patch("os.listdir", return_value=["players.sql", "teams.sql", "ignore.sql"])
@patch("os.path.isfile", return_value=True)
@patch("app.db.update.sql_dump_to_staging")
def test_load_sql_dumps_into_staging(mock_dump, mock_isfile, mock_listdir):
    mock_db = MagicMock()
    with patch("app.db.update.DUMP_INCLUSION_LIST", ["players", "teams"]):
        update_module.load_sql_dumps_into_staging(mock_db, "/dummy/path")
        assert mock_dump.call_count == 2


@patch("app.db.update.inject_db_path", side_effect=lambda sql, path: sql)
@patch("app.db.update.inject_heap_date", side_effect=lambda sql, heap_date: sql + " -- date injected")
def test_run_migration_sql(mock_inject_date, mock_inject_path, app):
    sql_content = "SELECT * FROM test;"
    mock_file = MagicMock()
    mock_file.read.return_value = sql_content

    with patch("app.db.update.current_app.open_resource") as mock_open:
        mock_open.return_value.__enter__.return_value = mock_file
        db = MagicMock()
        update_module.run_migration_sql(["dump", "2023", "08"], db)
        db.executescript.assert_called_once()


@patch("app.db.update.inject_heap_date", side_effect=lambda sql, heap_date: sql)
def test_fetch_projection_inputs(mock_inject, app):
    from types import SimpleNamespace

    sql_content = "SELECT * FROM players;"
    mock_file = MagicMock()
    mock_file.read.return_value = sql_content

    with patch("app.db.update.current_app.open_resource") as mock_open:
        mock_open.return_value.__enter__.return_value = mock_file
        rows = [{"id": 1}, {"id": 2}]
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [dict(row) for row in rows]
        db = MagicMock()
        db.execute.return_value = mock_cursor

        result = update_module.fetch_projection_inputs(["dump", "2023", "08"], db)
        assert result == rows


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
    mock_update.return_value = {"offense": [], "basepath": [], "defense": [], "value": []}
    db = MagicMock()
    projections = [{"id": i} for i in range(2500)]
    update_module.insert_projections(projections, db, batch_size=1000)
    
    # 3 calls: 2 for chunks, 1 final
    assert mock_update.call_count == 4
    # First call with projections
    assert mock_update.call_args_list[0][1]['inject'] is True
    # Last call with final=True
    assert mock_update.call_args_list[-1][1]['final'] is True


@patch("app.db.update.extract_heap_date_from_path", return_value=["dump", "2023", "08"])
@patch("app.db.update.connect_staging_db")
@patch("app.db.update.load_sql_dumps_into_staging")
@patch("app.db.update.run_migration_sql")
@patch("app.db.update.fetch_projection_inputs", return_value=[{"id": 1}, {"id": 2}])
@patch("app.db.update.project_players", return_value=[{"id": 1}, {"id": 2}])
@patch("app.db.update.insert_projections")
def test_process_single_heap(mock_insert, mock_project, mock_fetch, mock_migration,
                              mock_load, mock_connect, mock_extract):
    mock_logger = MagicMock()
    mock_db = MagicMock()
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn

    update_module.process_single_heap("/dummy/heap_path", 1, 10, mock_db, mock_logger)

    mock_connect.assert_called_once()
    mock_conn.commit.assert_called_once()
    mock_conn.close.assert_called_once()
    mock_insert.assert_called_once()
    mock_logger.info.assert_any_call("Number of players: 2")
