import pytest

from unittest.mock import MagicMock, patch

from app.db import cli as db_cli


@patch("app.db.cli.check_new_heaps", return_value=([],[]))
@patch("app.db.cli.get_db")
@patch("app.db.cli.close_db")
def test_update_db_no_heaps(mock_close, mock_get_db, mock_check, app):

    with patch("app.db.cli.current_app.logger") as mock_logger:
        db_cli.update_db()

    mock_logger.info.assert_called_with("No new heaps found.")
    mock_close.assert_not_called()


@patch("app.db.cli.process_single_heap")
@patch("app.db.cli.check_new_heaps", return_value=(["short1", "short2"], ["long1"]))
@patch("app.db.cli.get_db")
@patch("app.db.cli.close_db")
def test_update_db_with_heaps(mock_close, mock_get_db, mock_check, mock_process, app):
    mock_logger = MagicMock()
    mock_db = MagicMock()
    mock_get_db.return_value = mock_db

    with patch("app.db.cli.current_app.logger", mock_logger):
        db_cli.update_db()

    # Ensure logger reported discovery of heaps
    mock_logger.info.assert_any_call("Found 1 new long heap(s) and 2 new short heap(s).")
    mock_logger.info.assert_any_call("Migrating long heaps")
    mock_logger.info.assert_any_call("Migrating short heaps")
    mock_logger.info.assert_any_call("Migration and projection complete!")

    # Validate calls to process_single_heap with correct arguments
    mock_process.assert_any_call("long1", 1, 2, mock_db, short_heap=False)
    mock_process.assert_any_call("short1", 1, 2, mock_db, short_heap=True)
    mock_process.assert_any_call("short2", 2, 2, mock_db, short_heap=True)

    assert mock_process.call_count == 3

    mock_close.assert_called_once()
    mock_get_db.assert_called_once()
