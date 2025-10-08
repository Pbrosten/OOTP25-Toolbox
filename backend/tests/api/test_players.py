import pytest
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


# Test GET /api/players/search?q=Alice
@patch("app.api.players.get_db")
@patch("app.api.players.close_db")
def test_search_players(mock_close_db, mock_get_db, client):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        {"player_id": 1, "first_name": "Alice", "last_name": "Smith", "position": "C", "team_abbr": "NY"},
        {"player_id": 2, "first_name": "Alicia", "last_name": "Jones", "position": "SS", "team_abbr": "LA"},
    ]
    mock_con.execute.return_value = mock_cursor
    mock_get_db.return_value = mock_con

    response = client.get("/api/players/search?q=Ali")
    assert response.status_code == 200
    assert len(response.get_json()) == 2

    mock_get_db.assert_called_once()
    mock_close_db.assert_called_once()

# Test GET /api/players/<id>/details - Found
@patch("app.api.players.get_db")
@patch("app.api.players.close_db")
@patch("app.api.players.current_app.open_resource")
def test_get_player_details_by_id_found(mock_open_resource, mock_close_db, mock_get_db, client):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"player_id": 1, "name": "Alice", "position": "C"}
    mock_con.execute.return_value = mock_cursor
    mock_get_db.return_value = mock_con

    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT * FROM details WHERE player_id = ?"

    response = client.get("/api/players/1/details")
    assert response.status_code == 200
    assert response.get_json()["player_id"] == 1

    mock_open_resource.assert_called_once()
    mock_get_db.assert_called_once()
    mock_close_db.assert_called_once()

# Test GET /api/players/<id>/details - Not Found
@patch("app.api.players.get_db")
@patch("app.api.players.close_db")
@patch("app.api.players.current_app.open_resource")
def test_get_player_details_by_id_not_found(mock_open_resource, mock_close_db, mock_get_db, client):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    mock_con.execute.return_value = mock_cursor
    mock_get_db.return_value = mock_con

    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT * FROM details WHERE player_id = ?"

    response = client.get("/api/players/999/details")
    assert response.status_code == 404
    assert response.get_json() == {"error": "Player not found"}

    mock_open_resource.assert_called_once()
    mock_get_db.assert_called_once()
    mock_close_db.assert_called_once()

# Test GET /api/players/<id>/career/batting - MLB player
@patch("app.api.players.get_db")
@patch("app.api.players.close_db")
@patch("app.api.players.current_app.open_resource")
def test_get_player_career_batting_mlb(mock_open_resource, mock_close_db, mock_get_db, client):
    mock_con = MagicMock()
    
    # First query to check for MLB stats
    check_cursor = MagicMock()
    check_cursor.fetchone.return_value = (1,)  # Player has MLB stats
    mock_con.execute.side_effect = [
        check_cursor,  # for MLB check
        MagicMock(fetchall=MagicMock(return_value=[{"season": "2021", "avg": .300}]))  # actual data
    ]
    mock_get_db.return_value = mock_con

    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT * FROM mlb_stats WHERE player_id = :player_id"

    response = client.get("/api/players/1/career/batting")
    assert response.status_code == 200
    assert isinstance(response.get_json(), list)
    assert response.get_json()[0]["season"] == "2021"

    mock_open_resource.assert_called_once()
    mock_get_db.assert_called_once()
    mock_close_db.assert_called_once()

# Test GET /api/players/<id>/career/batting - No stats
@patch("app.api.players.get_db")
@patch("app.api.players.close_db")
@patch("app.api.players.current_app.open_resource")
def test_get_player_career_batting_not_found(mock_open_resource, mock_close_db, mock_get_db, client):
    mock_con = MagicMock()
    
    # No MLB stats
    check_cursor = MagicMock()
    check_cursor.fetchone.return_value = None
    # No MiLB stats found
    stats_cursor = MagicMock()
    stats_cursor.fetchall.return_value = []

    mock_con.execute.side_effect = [check_cursor, stats_cursor]
    mock_get_db.return_value = mock_con

    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT * FROM milb_stats WHERE player_id = :player_id"

    response = client.get("/api/players/999/career/batting")
    assert response.status_code == 404
    assert response.get_json() == {"error": "Player not found"}

    mock_open_resource.assert_called_once()
    mock_get_db.assert_called_once()
    mock_close_db.assert_called_once()

# Test GET /api/players/<id>/ratings - all ratings
@patch("app.api.players.get_db")
@patch("app.api.players.close_db")
@patch("app.api.players.current_app.open_resource")
def test_get_player_ratings_all(mock_open_resource, mock_close_db, mock_get_db, client):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        {"rating_id": 1, "overall": 50},
        {"rating_id": 2, "overall": 55},
    ]
    mock_con.execute.return_value = mock_cursor
    mock_get_db.return_value = mock_con

    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT * FROM ratings WHERE player_id = ?"

    response = client.get("/api/players/1/ratings")
    assert response.status_code == 200
    assert len(response.get_json()) == 2

# Test GET /api/players/<id>/ratings?latest=true
@patch("app.api.players.get_db")
@patch("app.api.players.close_db")
@patch("app.api.players.current_app.open_resource")
def test_get_player_ratings_latest(mock_open_resource, mock_close_db, mock_get_db, client):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [{"rating_id": 2, "overall": 55}]
    mock_con.execute.return_value = mock_cursor
    mock_get_db.return_value = mock_con

    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT * FROM ratings WHERE player_id = ?"

    response = client.get("/api/players/1/ratings?latest=true")
    assert response.status_code == 200
    assert isinstance(response.get_json(), dict)
    assert response.get_json()["rating_id"] == 2

# Test GET /api/players/<id>/ratings - not found
@patch("app.api.players.get_db")
@patch("app.api.players.close_db")
@patch("app.api.players.current_app.open_resource")
def test_get_player_ratings_not_found(mock_open_resource, mock_close_db, mock_get_db, client):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    mock_con.execute.return_value = mock_cursor
    mock_get_db.return_value = mock_con

    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT * FROM ratings WHERE player_id = ?"

    response = client.get("/api/players/999/ratings")
    assert response.status_code == 404
    assert response.get_json() == {"error": "Player ratings not found"}
