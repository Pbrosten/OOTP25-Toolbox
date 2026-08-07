from unittest.mock import patch

from app.db import cli as db_cli


@patch("app.db.cli.init_database", return_value={"status": "ok"})
def test_init_db_command_delegates_to_service(mock_init_database, app):
    runner = app.test_cli_runner()
    result = runner.invoke(db_cli.init_db_command)

    mock_init_database.assert_called_once_with()
    assert "Initialized the database." in result.output
    assert result.exit_code == 0


@patch(
    "app.db.cli.update_database",
    return_value={"status": "ok", "heaps_processed": 2, "long_heaps": 1, "short_heaps": 1},
)
def test_update_db_command_delegates_to_service(mock_update_database, app):
    runner = app.test_cli_runner()
    result = runner.invoke(db_cli.update_db_command)

    mock_update_database.assert_called_once_with()
    assert "Updated the database." in result.output
    assert result.exit_code == 0
