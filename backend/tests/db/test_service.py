from unittest.mock import MagicMock, patch

from app.db import service


@patch("app.db.service.close_db")
@patch("app.db.service.get_db")
@patch("app.db.service.check_new_heaps", return_value=[])
def test_update_database_no_heaps(mock_check, mock_get_db, mock_close, app):
    mock_db = MagicMock()
    mock_get_db.return_value = mock_db

    result = service.update_database()

    assert result == {
        "status": "ok",
        "heaps_processed": 0,
        "long_heaps": 0,
        "short_heaps": 0,
    }
    # get_db/close_db are now always called (not just when there are heaps
    # to process), since acquiring/releasing the cross-process update lock
    # (GET_LOCK/RELEASE_LOCK) needs a connection regardless. See ticket 0010.
    mock_get_db.assert_called_once()
    mock_close.assert_called_once()


@patch("app.db.service.process_single_heap")
@patch("app.db.service.close_db")
@patch("app.db.service.get_db")
@patch(
    "app.db.service.check_new_heaps",
    return_value=[("long1", False), ("short1", True), ("short2", True)],
)
def test_update_database_with_heaps(
    mock_check, mock_get_db, mock_close, mock_process, app
):
    mock_db = MagicMock()
    mock_get_db.return_value = mock_db

    result = service.update_database()

    assert result == {
        "status": "ok",
        "heaps_processed": 3,
        "long_heaps": 1,
        "short_heaps": 2,
    }

    mock_process.assert_any_call("long1", 1, 3, mock_db, short_heap=False)
    mock_process.assert_any_call("short1", 2, 3, mock_db, short_heap=True)
    mock_process.assert_any_call("short2", 3, 3, mock_db, short_heap=True)
    assert mock_process.call_count == 3

    mock_db.commit.assert_called_once()
    mock_close.assert_called_once()


@patch("app.db.service.close_db")
@patch("app.db.service.get_db")
def test_init_database(mock_get_db, mock_close, app):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_get_db.return_value = mock_conn

    with patch.object(
        app, "open_resource", return_value=MockResource("CREATE TABLE foo (id INT);")
    ):
        result = service.init_database()

    assert result == {"status": "ok"}
    mock_cursor.execute.assert_called_once_with("CREATE TABLE foo (id INT)")
    mock_conn.commit.assert_called_once()
    mock_close.assert_called_once()


class MockResource:
    def __init__(self, content):
        self._content = content

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self._content
