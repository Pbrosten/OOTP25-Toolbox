import os
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


def _leaderboard_row(**overrides):
    """Matches get_prospect_leaderboard.sql's flat output shape."""
    row = {
        "player_id": 1, "first_name": "Alice", "last_name": "Ace",
        "position": "SS", "age": 20, "team_id": 5, "team_abbr": "AAA",
        "org_abbr": "COL", "level": 2, "parent_team_id": 1, "mlb_service_years": 0,
        "fv": 60, "surplus_value": 82_000_000, "expected_war": 12.5,
        "star_odds": 33.0, "current_fv": 40, "risk_tag": "+",
    }
    row.update(overrides)
    return row


def _mock_leaderboard_db(mock_get_db, rows):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = rows
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con
    return mock_con, mock_cursor


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


def _fv30_row(**overrides):
    # Bottom-of-scale ratings across the board -- both talent and current
    # -- to guarantee an "Up & Down" FV 30 grade (see HITTER_WAR_TO_FV).
    row = _prospect_row(
        bat_babip=20, bat_gap=20, bat_eye=20, bat_power=20, bat_strikeouts=20,
        bat_babip_talent=20, bat_gap_talent=20, bat_eye_talent=20,
        bat_power_talent=20, bat_strikeouts_talent=20,
        speed=20, steal=20, baserunning=20,
        **{f"pos{i}": 20 for i in range(2, 10)},
        **{f"pos{i}_talent": 20 for i in range(2, 10)},
    )
    row.update(overrides)
    return row


@patch("app.api.prospects.current_app.open_resource")
@patch("app.api.prospects.close_db")
@patch("app.api.prospects.get_db")
def test_get_prospects_excludes_fv30_players(
    mock_get_db, mock_close_db, mock_open_resource, client
):
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."
    # No trend fetchall calls expected -- the row is excluded before
    # _trend_for runs, so only the initial get_prospects.sql fetchall fires.
    _mock_db(mock_get_db, [_fv30_row()], trend_rows_per_player=[])

    response = client.get("/api/prospects")

    assert response.status_code == 200
    body = response.get_json()
    assert body == []


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
def test_get_prospect_value_excludes_fv30_player(
    mock_get_db, mock_close_db, mock_open_resource, client
):
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = _fv30_row()
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con

    response = client.get("/api/prospects/1")

    assert response.status_code == 200
    assert response.get_json() == {"is_prospect": False}


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


# === leaderboard mode (ticket 0076) ===


@patch("app.api.prospects.current_app.open_resource")
@patch("app.api.prospects.close_db")
@patch("app.api.prospects.get_db")
def test_leaderboard_uses_get_prospect_leaderboard_sql(
    mock_get_db, mock_close_db, mock_open_resource, client
):
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."
    _mock_leaderboard_db(mock_get_db, [_leaderboard_row()])

    response = client.get("/api/prospects?leaderboard=1")

    assert response.status_code == 200
    expected_path = os.path.join("db", "sql_scripts", "api", "get_prospect_leaderboard.sql")
    mock_open_resource.assert_called_once_with(expected_path, "r")


@patch("app.api.prospects.current_app.open_resource")
@patch("app.api.prospects.close_db")
@patch("app.api.prospects.get_db")
def test_leaderboard_response_shape(mock_get_db, mock_close_db, mock_open_resource, client):
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."
    _mock_leaderboard_db(mock_get_db, [_leaderboard_row()])

    body = client.get("/api/prospects?leaderboard=1").get_json()

    assert set(body.keys()) == {"top_overall", "top_by_position", "top_by_level"}
    assert body["top_overall"]["page"] == 1
    assert body["top_overall"]["total"] == 1
    entry = body["top_overall"]["results"][0]
    assert entry["value"]["available"] is True
    assert entry["value"]["fv"] == 60
    assert entry["org_abbr"] == "COL"
    assert "trend" not in entry
    assert body["top_by_position"]["SS"][0]["player_id"] == 1
    assert body["top_by_level"]["2"][0]["player_id"] == 1


@patch("app.api.prospects.current_app.open_resource")
@patch("app.api.prospects.close_db")
@patch("app.api.prospects.get_db")
def test_leaderboard_mlb_level_omits_promotion_ready(
    mock_get_db, mock_close_db, mock_open_resource, client
):
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."
    _mock_leaderboard_db(mock_get_db, [_leaderboard_row(level=1)])

    body = client.get("/api/prospects?leaderboard=1").get_json()

    assert "mlb_promotion_ready" not in body["top_overall"]["results"][0]["value"]


@patch("app.api.prospects.current_app.open_resource")
@patch("app.api.prospects.close_db")
@patch("app.api.prospects.get_db")
def test_leaderboard_excludes_fv30(mock_get_db, mock_close_db, mock_open_resource, client):
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."
    _mock_leaderboard_db(mock_get_db, [_leaderboard_row(fv=30)])

    body = client.get("/api/prospects?leaderboard=1").get_json()

    assert body["top_overall"]["results"] == []
    assert body["top_by_position"] == {}
    assert body["top_by_level"] == {}


@patch("app.api.prospects.current_app.open_resource")
@patch("app.api.prospects.close_db")
@patch("app.api.prospects.get_db")
def test_leaderboard_sections_group_by_position_and_level(
    mock_get_db, mock_close_db, mock_open_resource, client
):
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."
    rows = [
        _leaderboard_row(player_id=1, position="SS", level=2, fv=70),
        _leaderboard_row(player_id=2, position="1B", level=2, fv=60),
        _leaderboard_row(player_id=3, position="SS", level=3, fv=50),
    ]
    _mock_leaderboard_db(mock_get_db, rows)

    body = client.get("/api/prospects?leaderboard=1").get_json()

    assert [p["player_id"] for p in body["top_by_position"]["SS"]] == [1, 3]
    assert [p["player_id"] for p in body["top_by_position"]["1B"]] == [2]
    assert [p["player_id"] for p in body["top_by_level"]["2"]] == [1, 2]
    assert [p["player_id"] for p in body["top_by_level"]["3"]] == [3]
    assert len(body["top_overall"]["results"]) == 3


@patch("app.api.prospects.current_app.open_resource")
@patch("app.api.prospects.close_db")
@patch("app.api.prospects.get_db")
def test_leaderboard_section_size_caps_at_ten(
    mock_get_db, mock_close_db, mock_open_resource, client
):
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."
    rows = [
        _leaderboard_row(player_id=i, position="SS", level=2, fv=80 - i)
        for i in range(15)
    ]
    _mock_leaderboard_db(mock_get_db, rows)

    body = client.get("/api/prospects?leaderboard=1").get_json()

    assert len(body["top_by_position"]["SS"]) == 10
    assert len(body["top_by_level"]["2"]) == 10
    assert [p["player_id"] for p in body["top_by_position"]["SS"]] == list(range(10))


@patch("app.api.prospects.current_app.open_resource")
@patch("app.api.prospects.close_db")
@patch("app.api.prospects.get_db")
def test_leaderboard_top_overall_pagination(
    mock_get_db, mock_close_db, mock_open_resource, client
):
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."
    rows = [_leaderboard_row(player_id=i, fv=80 - i) for i in range(5)]
    _mock_leaderboard_db(mock_get_db, rows)

    body = client.get("/api/prospects?leaderboard=1&page=2&page_size=2").get_json()

    assert body["top_overall"]["page"] == 2
    assert body["top_overall"]["page_size"] == 2
    assert body["top_overall"]["total"] == 5
    assert [p["player_id"] for p in body["top_overall"]["results"]] == [2, 3]


@patch("app.api.prospects.current_app.open_resource")
@patch("app.api.prospects.close_db")
@patch("app.api.prospects.get_db")
def test_leaderboard_default_page_size(
    mock_get_db, mock_close_db, mock_open_resource, client
):
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."
    _mock_leaderboard_db(mock_get_db, [_leaderboard_row()])

    body = client.get("/api/prospects?leaderboard=1").get_json()

    assert body["top_overall"]["page_size"] == 20


@patch("app.api.prospects.current_app.open_resource")
@patch("app.api.prospects.close_db")
@patch("app.api.prospects.get_db")
def test_leaderboard_passes_filters_to_query(
    mock_get_db, mock_close_db, mock_open_resource, client
):
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."
    _, mock_cursor = _mock_leaderboard_db(mock_get_db, [])

    client.get("/api/prospects?leaderboard=1&team_id=5&position=SS&level=2")

    call_args = mock_cursor.execute.call_args_list[0]
    assert call_args.args[1] == {"team_id": 5, "position": "SS", "level": 2}


@patch("app.api.prospects.current_app.open_resource")
@patch("app.api.prospects.close_db")
@patch("app.api.prospects.get_db")
def test_leaderboard_does_not_query_trends(
    mock_get_db, mock_close_db, mock_open_resource, client
):
    # Leaderboard mode reads only the persisted table -- no per-player
    # get_player_rating_trends.sql calls (unlike the org-scoped mode).
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."
    _, mock_cursor = _mock_leaderboard_db(mock_get_db, [_leaderboard_row()])

    client.get("/api/prospects?leaderboard=1")

    assert mock_cursor.execute.call_count == 1
