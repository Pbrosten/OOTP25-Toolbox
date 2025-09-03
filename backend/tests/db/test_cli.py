import pytest

from unittest.mock import MagicMock, patch

from app.db import cli as db_cli


@patch("app.db.cli.check_new_heaps", return_value=[])
@patch("app.db.cli.get_db")
@patch("app.db.cli.close_db")
def test_update_db_no_heaps(mock_close, mock_get_db, mock_check, app):

    with patch("app.db.cli.current_app.logger") as mock_logger:
        db_cli.update_db()

    mock_logger.info.assert_called_with("No new heaps found.")
    mock_close.assert_not_called()


@patch("app.db.cli.process_single_heap")
@patch("app.db.cli.check_new_heaps", return_value=["/path/to/heap1", "/path/to/heap2"])
@patch("app.db.cli.get_db")
@patch("app.db.cli.close_db")
def test_update_db_with_heaps(mock_close, mock_get_db, mock_check, mock_process, app):

    mock_logger = MagicMock()
    mock_db = MagicMock()
    mock_get_db.return_value = mock_db

    with patch("app.db.cli.current_app.logger", mock_logger):
        db_cli.update_db()

    # Check heap processing
    assert mock_process.call_count == 2
    mock_process.assert_any_call("/path/to/heap1", 1, 2, mock_db, mock_logger)
    mock_process.assert_any_call("/path/to/heap2", 2, 2, mock_db, mock_logger)

    mock_close.assert_called_once()
    mock_logger.info.assert_any_call("Migration and projection complete!")
