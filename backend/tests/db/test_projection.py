import pytest
from unittest.mock import patch, MagicMock
from app.db import projection as projection_module

@patch("app.db.projection.BatterProjection")
def test_process_player_success(mock_batter_proj, app):
    fake_player = {"rating_id": 123}
    mock_instance = mock_batter_proj.return_value
    mock_instance.calc_expected_stats.return_value = {"offense": {"rating_id": 123}}

    with app.app_context():
        result = projection_module.process_player(fake_player)

    mock_batter_proj.assert_called_once_with(fake_player)
    mock_instance.calc_expected_stats.assert_called_once()
    assert result == {"offense": {"rating_id": 123}}


@patch("app.db.projection.BatterProjection")
def test_process_player_returns_none_logs_warning(mock_batter_proj):
    fake_player = {"rating_id": 456}
    mock_instance = mock_batter_proj.return_value
    mock_instance.calc_expected_stats.return_value = None

    # process_player runs in a multiprocessing worker with no Flask app
    # context, so it must log via a plain module-level logger, not
    # current_app.logger -- see docs/tickets/0012.
    with patch("app.db.projection.logger") as mock_logger:
        result = projection_module.process_player(fake_player)

    assert result is None
    mock_logger.warning.assert_called_once_with("No result for player: 456")


@patch("app.db.projection.BatterProjection", side_effect=Exception("fail"))
def test_process_player_exception(mock_batter_proj):
    fake_player = {"rating_id": 789}

    with patch("app.db.projection.logger") as mock_logger:
        result = projection_module.process_player(fake_player)

    assert result is None
    mock_logger.warning.assert_called_once()
    assert "Error processing player 789" in mock_logger.warning.call_args[0][0]


def test_update_projection_batches_final_commits_and_returns_rows_written():
    # update_projection_batches returns (batches_or_None, rows_written) when
    # inject/final -- see docs/tickets/0016.
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.rowcount = 3
    mock_db.cursor.return_value.__enter__.return_value = mock_cursor
    mock_batches = {
        "offense": [{"rating_id": 1}],
        "value": [],
    }

    batches, rows_written = projection_module.update_projection_batches(
        mock_batches, db=mock_db, final=True
    )

    mock_cursor.executemany.assert_called_once_with(
        projection_module.proj_scripts["offense"], [{"rating_id": 1}]
    )
    mock_db.commit.assert_called_once()
    assert batches is None
    assert rows_written == 3


def test_update_projection_batches_inject_returns_empty_batches_and_rows_written():
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.rowcount = 1
    mock_db.cursor.return_value.__enter__.return_value = mock_cursor
    batches = {
        "offense": [{"rating_id": 1}],
        "value": [{"rating_id": 2}],
    }

    result, rows_written = projection_module.update_projection_batches(
        batches.copy(), db=mock_db, inject=True
    )

    assert result == {"offense": [], "value": []}
    assert mock_cursor.executemany.call_count == 2
    mock_db.commit.assert_called_once()
    assert rows_written == 2  # 1 rowcount from each of the 2 executemany calls


def test_update_projection_batches_with_projections_appends_to_batches():
    projections = [
        {
            "offense": {"rating_id": 1},
            "value": {"rating_id": 2},
            "basepath": None
        },
        {
            "offense": {"rating_id": 3},
            "value": {"rating_id": 4},
        },
    ]
    batches = {"offense": [], "value": [], "basepath": []}

    updated_batches = projection_module.update_projection_batches(
        batches, projections=projections
    )

    assert updated_batches["offense"] == [{"rating_id": 1}, {"rating_id": 3}]
    assert updated_batches["value"] == [{"rating_id": 2}, {"rating_id": 4}]
    assert updated_batches["basepath"] == []
