from unittest.mock import MagicMock, patch


def _depth_chart_row(**overrides):
    row = {
        "player_id": 1,
        "first_name": "Alice",
        "last_name": "Ace",
        "team_id": 1,
        "level": 1,
        "position": "SS",
        "role_group": None,
        "war": 2.5,
    }
    row.update(overrides)
    return row


# Test GET /api/teams/<id>/depth-chart - not an MLB team (level != 1)
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
def test_get_team_depth_chart_non_mlb_team_not_found(mock_close_db, mock_get_db, client):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"level": 2}
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con

    response = client.get("/api/teams/59/depth-chart")
    assert response.status_code == 404


# Test GET /api/teams/<id>/depth-chart - unknown team_id
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
def test_get_team_depth_chart_unknown_team_not_found(mock_close_db, mock_get_db, client):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con

    response = client.get("/api/teams/99999/depth-chart")
    assert response.status_code == 404


# Test GET /api/teams/<id>/depth-chart - groups by position, sorted by WAR desc
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
@patch("app.api.teams.current_app.open_resource")
def test_get_team_depth_chart_groups_by_position_sorted_by_war(
    mock_open_resource, mock_close_db, mock_get_db, client
):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"level": 1}
    mock_cursor.fetchall.return_value = [
        _depth_chart_row(player_id=1, last_name="Low", war=1.0),
        _depth_chart_row(player_id=2, last_name="High", war=4.0),
    ]
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."

    response = client.get("/api/teams/1/depth-chart")
    assert response.status_code == 200
    body = response.get_json()
    assert body["team_id"] == 1
    players = body["levels"]["1"]["SS"]
    assert [p["last_name"] for p in players] == ["High", "Low"]


# Pitchers group by role_group (SP/RP), not the raw "P" position.
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
@patch("app.api.teams.current_app.open_resource")
def test_get_team_depth_chart_pitchers_grouped_by_role(
    mock_open_resource, mock_close_db, mock_get_db, client
):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"level": 1}
    mock_cursor.fetchall.return_value = [
        _depth_chart_row(player_id=3, position="P", role_group="SP", war=2.0),
        _depth_chart_row(player_id=4, position="P", role_group="RP", war=1.0),
    ]
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."

    response = client.get("/api/teams/1/depth-chart")
    body = response.get_json()
    assert len(body["levels"]["1"]["SP"]) == 1
    assert len(body["levels"]["1"]["RP"]) == 1
    assert "P" not in body["levels"]["1"]


# A player with no current WAR (e.g. a two-way player, per the query's
# never-net-batting/pitching precedent) sorts last, not excluded.
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
@patch("app.api.teams.current_app.open_resource")
def test_get_team_depth_chart_null_war_sorts_last(
    mock_open_resource, mock_close_db, mock_get_db, client
):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"level": 1}
    mock_cursor.fetchall.return_value = [
        _depth_chart_row(player_id=5, last_name="NoWar", war=None),
        _depth_chart_row(player_id=6, last_name="HasWar", war=0.5),
    ]
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."

    response = client.get("/api/teams/1/depth-chart")
    players = response.get_json()["levels"]["1"]["SS"]
    assert [p["last_name"] for p in players] == ["HasWar", "NoWar"]


# Multiple levels/groups are kept separate.
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
@patch("app.api.teams.current_app.open_resource")
def test_get_team_depth_chart_separates_levels(
    mock_open_resource, mock_close_db, mock_get_db, client
):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"level": 1}
    mock_cursor.fetchall.return_value = [
        _depth_chart_row(player_id=7, team_id=1, level=1, last_name="MLBPlayer"),
        _depth_chart_row(player_id=8, team_id=59, level=2, last_name="AAAPlayer"),
    ]
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."

    response = client.get("/api/teams/1/depth-chart")
    body = response.get_json()
    assert body["levels"]["1"]["SS"][0]["last_name"] == "MLBPlayer"
    assert body["levels"]["2"]["SS"][0]["last_name"] == "AAAPlayer"
