from unittest.mock import MagicMock, patch


# Test GET /api/teams - MLB team listing for the depth-chart picker
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
def test_get_mlb_teams(mock_close_db, mock_get_db, client):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        {"team_id": 1, "name": "Arizona", "abbr": "AZ", "nickname": "Diamondbacks"},
        {"team_id": 2, "name": "Atlanta", "abbr": "ATL", "nickname": "Braves"},
    ]
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con

    response = client.get("/api/teams")
    assert response.status_code == 200
    body = response.get_json()
    assert len(body) == 2
    assert body[0]["team_id"] == 1


def _depth_chart_row(**overrides):
    row = {
        "player_id": 1,
        "first_name": "Alice",
        "last_name": "Ace",
        "team_id": 1,
        "team_abbr": "AZ",
        "level": 1,
        "position": "SS",
        "role_group": None,
        "is_twp": 0,
        "war": 2.5,
        "is_promotion_candidate": 0,
    }
    row.update(overrides)
    return row


def _team_row(**overrides):
    row = {
        "level": 1,
        "city_id": 58739,
        "name": "Arizona",
        "nickname": "Diamondbacks",
        "background_color": "#AA182C",
        "text_color": "#3EC1CC",
    }
    row.update(overrides)
    return row


# Test GET /api/teams/<id>/depth-chart - not an MLB team (level != 1)
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
def test_get_team_depth_chart_non_mlb_team_not_found(mock_close_db, mock_get_db, client):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = _team_row(level=2, city_id=12345)
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con

    response = client.get("/api/teams/59/depth-chart")
    assert response.status_code == 404


# Test GET /api/teams/<id>/depth-chart - level=1 exhibition team (no real
# city, e.g. this save's AL/NL All-Stars/Future Stars) is not a real team
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
def test_get_team_depth_chart_exhibition_team_not_found(mock_close_db, mock_get_db, client):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = _team_row(city_id=0)
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con

    response = client.get("/api/teams/31/depth-chart")
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
    mock_cursor.fetchone.return_value = _team_row()
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
    mock_cursor.fetchone.return_value = _team_row()
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
    mock_cursor.fetchone.return_value = _team_row()
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
    mock_cursor.fetchone.return_value = _team_row()
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


# Team metadata for frontend theming (ticket 0064).
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
@patch("app.api.teams.current_app.open_resource")
def test_get_team_depth_chart_includes_team_metadata(
    mock_open_resource, mock_close_db, mock_get_db, client
):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = _team_row(
        name="Arizona", nickname="Diamondbacks",
        background_color="#AA182C", text_color="#3EC1CC",
    )
    mock_cursor.fetchall.return_value = [_depth_chart_row()]
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."

    response = client.get("/api/teams/1/depth-chart")
    body = response.get_json()
    assert body["team_name"] == "Arizona Diamondbacks"
    assert body["background_color"] == "#AA182C"
    assert body["text_color"] == "#3EC1CC"


# A/Rookie levels (4, 6) return a roster count per position, not a
# WAR-ranked player list -- current-rating WAR isn't a meaningful ranking
# signal that far from MLB-readiness (ticket 0064).
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
@patch("app.api.teams.current_app.open_resource")
def test_get_team_depth_chart_count_only_levels(
    mock_open_resource, mock_close_db, mock_get_db, client
):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = _team_row()
    mock_cursor.fetchall.return_value = [
        _depth_chart_row(player_id=10, level=4, position="SS"),
        _depth_chart_row(player_id=11, level=4, position="SS"),
        _depth_chart_row(player_id=12, level=6, position="C"),
    ]
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."

    response = client.get("/api/teams/1/depth-chart")
    body = response.get_json()
    assert body["levels"]["4"]["SS"] == 2
    assert body["levels"]["6"]["C"] == 1


# is_promotion_candidate (AAA/AA only, top 20% of league-wide WAR at that
# level) passes through to the player entry.
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
@patch("app.api.teams.current_app.open_resource")
def test_get_team_depth_chart_promotion_candidate_flag(
    mock_open_resource, mock_close_db, mock_get_db, client
):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = _team_row()
    mock_cursor.fetchall.return_value = [
        _depth_chart_row(player_id=13, level=2, is_promotion_candidate=1),
        _depth_chart_row(player_id=14, level=2, is_promotion_candidate=0),
    ]
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."

    response = client.get("/api/teams/1/depth-chart")
    players = {p["player_id"]: p for p in response.get_json()["levels"]["2"]["SS"]}
    assert players[13]["is_promotion_candidate"] is True
    assert players[14]["is_promotion_candidate"] is False


# is_twp takes priority over position for grouping (ticket 0067 post-close
# correction) -- a real TWP's listed position isn't always 'P' (confirmed
# real case: Shohei Ohtani is 'DH' but has real players_pitching data), so
# checking is_twp first keeps the depth chart consistent with the player
# page's identical is_twp check.
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
@patch("app.api.teams.current_app.open_resource")
def test_get_team_depth_chart_twp_groups_by_twp_even_when_position_not_pitcher(
    mock_open_resource, mock_close_db, mock_get_db, client
):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = _team_row()
    mock_cursor.fetchall.return_value = [
        _depth_chart_row(player_id=15, position="DH", role_group=None, is_twp=1),
    ]
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."

    response = client.get("/api/teams/1/depth-chart")
    body = response.get_json()
    assert "TWP" in body["levels"]["1"]
    assert body["levels"]["1"]["TWP"][0]["player_id"] == 15
    assert "DH" not in body["levels"]["1"]
