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
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
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
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
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
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
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
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
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
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
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
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
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

    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (1,)  # Player has MLB stats
    mock_cursor.fetchall.return_value = [{"season": "2021", "avg": .300}]  # actual data
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
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

    # No MLB stats, no MiLB stats found
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    mock_cursor.fetchall.return_value = []

    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
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
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
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
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
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
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con

    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT * FROM ratings WHERE player_id = ?"

    response = client.get("/api/players/999/ratings")
    assert response.status_code == 404
    assert response.get_json() == {"error": "Player ratings not found"}


def _contract_row(**overrides):
    row = {
        "age": 30,
        "prone_overall": None,
        "batting_war": 3.0,
        "pitching_war": None,
        "pitching_role": None,
        "mlb_service_years": 4,
        "current_year": 2,
        # years=3 (not 4): remaining_contract_years=1 -- one more signed
        # year, then a genuine discretionary arbitration-estimate year
        # before free agency (service 4+1=5 < FA_SERVICE_YEARS=6). A
        # contract covering the player's *entire* remaining horizon
        # (e.g. years=4 here, remaining=2, exactly reaching FA at
        # service 4+2=6) has no discretionary year at all -- ticket 0082
        # fix -- and recommend_contract_action correctly returns no
        # recommendation for that case, which isn't what most of these
        # tests are checking.
        "years": 3,
        # Ticket 0066: LEFT JOINed from the latest market_baselines row --
        # NULL/None until the save's first long heap has computed one.
        "war_dollar_value": None,
        "recommendation_extend_threshold": None,
    }
    row.update({f"salary{i}": 0 for i in range(15)})
    row["salary1"] = 10_000_000
    row["salary2"] = 12_000_000
    row.update(overrides)
    return row


# Test GET /api/players/<id>/surplus-value - real signed contract
@patch("app.api.players.get_db")
@patch("app.api.players.close_db")
@patch("app.api.players.current_app.open_resource")
def test_get_player_surplus_value_available(mock_open_resource, mock_close_db, mock_get_db, client):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = _contract_row()
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."

    response = client.get("/api/players/1/surplus-value")
    assert response.status_code == 200
    body = response.get_json()
    assert body["available"] is True
    assert len(body["years"]) > 0
    assert "recommendation" in body  # mlb_service_years=4 is arb-eligible


# Recommendation labels only apply during a player's arbitration window
# (ARB_ELIGIBLE_SERVICE_YEARS <= mlb_service_years < FA_SERVICE_YEARS) --
# per user report, showing "Extend"/"Non-tender"/etc. for a pre-arb rookie
# or a player already past free-agency service isn't the decision this
# label set describes.
@patch("app.api.players.get_db")
@patch("app.api.players.close_db")
@patch("app.api.players.current_app.open_resource")
def test_get_player_surplus_value_pre_arb_omits_recommendation(
    mock_open_resource, mock_close_db, mock_get_db, client
):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = _contract_row(mlb_service_years=1)
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."

    response = client.get("/api/players/1/surplus-value")
    assert response.status_code == 200
    body = response.get_json()
    assert body["available"] is True
    assert "recommendation" not in body


@patch("app.api.players.get_db")
@patch("app.api.players.close_db")
@patch("app.api.players.current_app.open_resource")
def test_get_player_surplus_value_past_free_agency_service_omits_recommendation(
    mock_open_resource, mock_close_db, mock_get_db, client
):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = _contract_row(mlb_service_years=8)
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."

    response = client.get("/api/players/1/surplus-value")
    assert response.status_code == 200
    body = response.get_json()
    assert body["available"] is True
    assert "recommendation" not in body


# Regression: OOTP writes a years=0/current_year=0 placeholder contract row
# for every unsigned player, not "no row" -- must not be read as a real
# 1-year deal (years=0 also wraps Python's salaries[-1] indexing).
@patch("app.api.players.get_db")
@patch("app.api.players.close_db")
@patch("app.api.players.current_app.open_resource")
def test_get_player_surplus_value_unsigned_placeholder_contract_not_available(
    mock_open_resource, mock_close_db, mock_get_db, client
):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = _contract_row(
        years=0, current_year=0, mlb_service_years=10
    )
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."

    response = client.get("/api/players/1/surplus-value")
    assert response.status_code == 200
    assert response.get_json() == {"available": False}


# Regression/coverage for ticket 0059: a Wrecked-durability player's
# future-year projected value should drop relative to an otherwise-identical
# Normal-durability player, while year 0 (already discounted upstream by
# BatterProjection/PitcherProjection) is untouched.
@patch("app.api.players.get_db")
@patch("app.api.players.close_db")
@patch("app.api.players.current_app.open_resource")
def test_get_player_surplus_value_wrecked_durability_discounts_future_years(
    mock_open_resource, mock_close_db, mock_get_db, client
):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."

    mock_cursor.fetchone.return_value = _contract_row(prone_overall=100)
    normal_body = client.get("/api/players/1/surplus-value").get_json()

    mock_cursor.fetchone.return_value = _contract_row(prone_overall=200)
    wrecked_body = client.get("/api/players/1/surplus-value").get_json()

    assert normal_body["years"][0]["value"] == wrecked_body["years"][0]["value"]
    assert wrecked_body["years"][1]["value"] < normal_body["years"][1]["value"]


# Two-way player: base_war is batting_war + pitching_war summed, not
# excluded (ticket 0067 post-close correction, per user request -- a
# deliberate change from 0056's original "exclude two-way entirely"
# precedent, scoped to this route only).
@patch("app.api.players.get_db")
@patch("app.api.players.close_db")
@patch("app.api.players.current_app.open_resource")
def test_get_player_surplus_value_two_way_sums_war(mock_open_resource, mock_close_db, mock_get_db, client):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = _contract_row(batting_war=2.0, pitching_war=1.5)
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."

    response = client.get("/api/players/1/surplus-value")
    assert response.status_code == 200
    body = response.get_json()
    assert body["available"] is True
    assert body["years"][0]["war"] == pytest.approx(3.5)


# Test GET /api/players/<id>/surplus-value - no row at all
@patch("app.api.players.get_db")
@patch("app.api.players.close_db")
@patch("app.api.players.current_app.open_resource")
def test_get_player_surplus_value_no_row_not_available(mock_open_resource, mock_close_db, mock_get_db, client):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."

    response = client.get("/api/players/1/surplus-value")
    assert response.status_code == 200
    assert response.get_json() == {"available": False}
