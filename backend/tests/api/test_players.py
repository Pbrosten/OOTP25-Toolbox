from unittest.mock import MagicMock, patch

# Test GET /api/players
@patch("app.api.players.get_db")
@patch("app.api.players.close_db")
def test_get_players(mock_close_db, mock_get_db, client):
    # Fake DB response
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        {"player_id": 1, "name": "Alice"},
        {"player_id": 2, "name": "Bob"},
    ]
    mock_con.execute.return_value = mock_cursor
    mock_get_db.return_value = mock_con

    response = client.get("/api/players")
    assert response.status_code == 200
    assert response.get_json() == [
        {"player_id": 1, "name": "Alice"},
        {"player_id": 2, "name": "Bob"},
    ]

    mock_get_db.assert_called_once()
    mock_close_db.assert_called_once()


# Test GET /api/players/<id> - Found
@patch("app.api.players.get_db")
@patch("app.api.players.close_db")
def test_get_player_by_id_found(mock_close_db, mock_get_db, client):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"player_id": 1, "name": "Alice"}
    mock_con.execute.return_value = mock_cursor
    mock_get_db.return_value = mock_con

    response = client.get("/api/players/1")
    assert response.status_code == 200
    assert response.get_json() == {"player_id": 1, "name": "Alice"}

    mock_get_db.assert_called_once()
    mock_close_db.assert_called_once()


# Test GET /api/players/<id> - Not Found
@patch("app.api.players.get_db")
@patch("app.api.players.close_db")
def test_get_player_by_id_not_found(mock_close_db, mock_get_db, client):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    mock_con.execute.return_value = mock_cursor
    mock_get_db.return_value = mock_con

    response = client.get("/api/players/999")
    assert response.status_code == 404
    assert response.get_json() == {"error": "Player not found"}

    mock_get_db.assert_called_once()
    mock_close_db.assert_called_once()
