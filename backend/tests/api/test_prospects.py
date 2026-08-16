from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from app.api.prospects import bp as prospects_bp


@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(prospects_bp)
    with app.app_context():
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


def _prospect_row(**overrides):
    row = {
        "player_id": 1, "first_name": "Alice", "last_name": "Ace",
        "position": "SS", "bats": "R", "birth_date": "2005-01-01",
        "age": 20, "prone_overall": 50, "team_id": 5, "team_abbr": "AAA",
        "level": 2, "parent_team_id": 1, "mlb_service_years": 0,
        "rating_id": 100, "rating_date": "2025-09-01",
        "bat_babip": 50, "bat_gap": 50, "bat_eye": 50, "bat_power": 50,
        "bat_strikeouts": 50,
        "bat_babip_talent": 70, "bat_gap_talent": 70, "bat_eye_talent": 70,
        "bat_power_talent": 70, "bat_strikeouts_talent": 70,
        "speed": 50, "steal": 50, "baserunning": 50,
        **{f"pos{i}": 50 for i in range(2, 10)},
        **{f"pos{i}_talent": 50 for i in range(2, 10)},
        "pitch_role": None, "pitch_stuff": None, "pitch_control": None,
        "pitch_pbabip": None, "pitch_hra": None, "pitch_stamina": None,
        "pitch_hold": None, "pitch_stuff_talent": None,
        "pitch_control_talent": None, "pitch_pbabip_talent": None,
        "pitch_hra_talent": None,
    }
    row.update(overrides)
    return row


def _pitcher_row(**overrides):
    row = _prospect_row(
        player_id=2, first_name="Bob", last_name="Bomber", position="P",
        pitch_role=11, pitch_stuff=50, pitch_control=50, pitch_pbabip=50,
        pitch_hra=50, pitch_stamina=50, pitch_hold=50,
        pitch_stuff_talent=70, pitch_control_talent=70,
        pitch_pbabip_talent=70, pitch_hra_talent=70,
    )
    row.update(overrides)
    return row


def _mock_db(mock_get_db, prospect_rows, trend_rows_per_player=None):
    """trend_rows_per_player: list of row-lists, one per prospect, returned
    in order from successive get_player_rating_trends.sql fetchall() calls."""
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.side_effect = [prospect_rows] + (
        trend_rows_per_player if trend_rows_per_player is not None
        else [[] for _ in prospect_rows]
    )
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con
    return mock_con, mock_cursor


@patch("app.api.prospects.current_app.open_resource")
@patch("app.api.prospects.close_db")
@patch("app.api.prospects.get_db")
def test_get_prospects_hitter_available(mock_get_db, mock_close_db, mock_open_resource, client):
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."
    _mock_db(mock_get_db, [_prospect_row()])

    response = client.get("/api/prospects")

    assert response.status_code == 200
    body = response.get_json()
    assert len(body) == 1
    prospect = body[0]
    assert prospect["player_id"] == 1
    assert prospect["value"]["available"] is True
    assert prospect["value"]["fv"] in {20, 30, 40, 45, 50, 55, 60, 70, 80}
    # level=2 (not MLB) -- readiness flag should be present.
    assert "mlb_promotion_ready" in prospect["value"]
    assert prospect["trend"] == {"direction": "flat", "alerts": []}


@patch("app.api.prospects.current_app.open_resource")
@patch("app.api.prospects.close_db")
@patch("app.api.prospects.get_db")
def test_get_prospects_mlb_level_omits_promotion_ready(
    mock_get_db, mock_close_db, mock_open_resource, client
):
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."
    _mock_db(mock_get_db, [_prospect_row(level=1, mlb_service_years=0)])

    response = client.get("/api/prospects")

    body = response.get_json()
    assert "mlb_promotion_ready" not in body[0]["value"]


@patch("app.api.prospects.current_app.open_resource")
@patch("app.api.prospects.close_db")
@patch("app.api.prospects.get_db")
def test_get_prospects_rp_role_available(
    mock_get_db, mock_close_db, mock_open_resource, client
):
    # RP is no longer excluded (ticket 0068 post-close correction, user
    # request) -- their own smaller workload baseline penalizes them
    # naturally rather than needing a hard exclusion.
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."
    _mock_db(mock_get_db, [_pitcher_row(pitch_role=12)])

    response = client.get("/api/prospects")

    body = response.get_json()
    assert body[0]["value"]["available"] is True


@patch("app.api.prospects.current_app.open_resource")
@patch("app.api.prospects.close_db")
@patch("app.api.prospects.get_db")
def test_get_prospects_sp_role_available(
    mock_get_db, mock_close_db, mock_open_resource, client
):
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."
    _mock_db(mock_get_db, [_pitcher_row(pitch_role=11)])

    response = client.get("/api/prospects")

    body = response.get_json()
    assert body[0]["value"]["available"] is True


@patch("app.api.prospects.current_app.open_resource")
@patch("app.api.prospects.close_db")
@patch("app.api.prospects.get_db")
def test_get_prospects_trend_direction_up(
    mock_get_db, mock_close_db, mock_open_resource, client
):
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."
    trend_rows = [
        {
            "table_name": "players_batting_talent", "column_name": "power",
            "delta": 15, "exceeded": True,
        }
    ]
    _mock_db(mock_get_db, [_prospect_row()], trend_rows_per_player=[trend_rows])

    response = client.get("/api/prospects")

    body = response.get_json()
    assert body[0]["trend"]["direction"] == "up"
    assert len(body[0]["trend"]["alerts"]) == 1


@patch("app.api.prospects.current_app.open_resource")
@patch("app.api.prospects.close_db")
@patch("app.api.prospects.get_db")
def test_get_prospects_passes_filters_to_query(
    mock_get_db, mock_close_db, mock_open_resource, client
):
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."
    _, mock_cursor = _mock_db(mock_get_db, [])

    response = client.get("/api/prospects?team_id=5&position=SS&level=2")

    assert response.status_code == 200
    first_call_args = mock_cursor.execute.call_args_list[0]
    assert first_call_args.args[1] == {
        "team_id": 5, "position": "SS", "level": 2, "player_id": None,
    }


@patch("app.api.prospects.current_app.open_resource")
@patch("app.api.prospects.close_db")
@patch("app.api.prospects.get_db")
def test_get_prospects_no_filters_pass_none(
    mock_get_db, mock_close_db, mock_open_resource, client
):
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."
    _, mock_cursor = _mock_db(mock_get_db, [])

    client.get("/api/prospects")

    first_call_args = mock_cursor.execute.call_args_list[0]
    assert first_call_args.args[1] == {
        "team_id": None, "position": None, "level": None, "player_id": None,
    }


@patch("app.api.prospects.current_app.open_resource")
@patch("app.api.prospects.close_db")
@patch("app.api.prospects.get_db")
def test_get_prospect_value_not_a_prospect(
    mock_get_db, mock_close_db, mock_open_resource, client
):
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con

    response = client.get("/api/prospects/999")

    assert response.status_code == 200
    assert response.get_json() == {"is_prospect": False}


@patch("app.api.prospects.current_app.open_resource")
@patch("app.api.prospects.close_db")
@patch("app.api.prospects.get_db")
def test_get_prospect_value_is_a_prospect(
    mock_get_db, mock_close_db, mock_open_resource, client
):
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = _prospect_row()
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con

    response = client.get("/api/prospects/1")

    assert response.status_code == 200
    body = response.get_json()
    assert body["is_prospect"] is True
    assert body["available"] is True
    assert "fv" in body
    assert "mlb_promotion_ready" in body  # level=2 in _prospect_row()


@patch("app.api.prospects.current_app.open_resource")
@patch("app.api.prospects.close_db")
@patch("app.api.prospects.get_db")
def test_get_prospect_value_passes_player_id_filter(
    mock_get_db, mock_close_db, mock_open_resource, client
):
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con

    client.get("/api/prospects/42")

    call_args = mock_cursor.execute.call_args_list[0]
    assert call_args.args[1] == {
        "team_id": None, "position": None, "level": None, "player_id": 42,
    }
