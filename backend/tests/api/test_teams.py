from unittest.mock import MagicMock, patch

import pytest


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


# Test GET /api/teams/<id>/war-summary - not an MLB team (level != 1)
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
def test_get_team_war_summary_non_mlb_team_not_found(mock_close_db, mock_get_db, client):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"level": 2, "city_id": 12345}
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con

    response = client.get("/api/teams/59/war-summary")
    assert response.status_code == 404


# Test GET /api/teams/<id>/war-summary - level=1 exhibition team (no real
# city) is not a real team, same exclusion as the depth-chart route.
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
def test_get_team_war_summary_exhibition_team_not_found(mock_close_db, mock_get_db, client):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"level": 1, "city_id": 0}
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con

    response = client.get("/api/teams/31/war-summary")
    assert response.status_code == 404


# Test GET /api/teams/<id>/war-summary - unknown team_id
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
def test_get_team_war_summary_unknown_team_not_found(mock_close_db, mock_get_db, client):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con

    response = client.get("/api/teams/99999/war-summary")
    assert response.status_code == 404


# Test GET /api/teams/<id>/war-summary - real MLB team returns the summed
# WAR aggregate plus its league power ranking from the query as-is
# (aggregation/ranking itself lives in SQL).
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
@patch("app.api.teams.current_app.open_resource")
def test_get_team_war_summary_returns_aggregate_and_rank(
    mock_open_resource, mock_close_db, mock_get_db, client
):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.side_effect = [
        {"level": 1, "city_id": 58739},
        {"war": 24.7, "team_rank": 5, "total_teams": 30},
    ]
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."

    response = client.get("/api/teams/1/war-summary")
    assert response.status_code == 200
    body = response.get_json()
    assert body == {"team_id": 1, "war": 24.7, "rank": 5, "total_teams": 30}


def _roster_strength_row(**overrides):
    # One row per (group, this team's player) pair, as
    # get_team_roster_strength.sql returns -- a group with nobody
    # rostered there is a single row with player_id/war/etc. all None.
    # league_pool_size is the same for every row in a group (it doesn't
    # depend on this team's player at all).
    row = {
        "group_code": "SS",
        "player_id": 1,
        "first_name": "Alice",
        "last_name": "Ace",
        "war": 2.0,
        "league_percentile": 60,
        "league_rank": 10,
        "league_pool_size": 100,
    }
    row.update(overrides)
    return row


# Test GET /api/teams/<id>/roster-strength - not an MLB team (level != 1)
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
def test_get_team_roster_strength_non_mlb_team_not_found(mock_close_db, mock_get_db, client):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"level": 2, "city_id": 12345}
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con

    response = client.get("/api/teams/59/roster-strength")
    assert response.status_code == 404


# Test GET /api/teams/<id>/roster-strength - level=1 exhibition team
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
def test_get_team_roster_strength_exhibition_team_not_found(mock_close_db, mock_get_db, client):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"level": 1, "city_id": 0}
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con

    response = client.get("/api/teams/31/roster-strength")
    assert response.status_code == 404


# Test GET /api/teams/<id>/roster-strength - unknown team_id
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
def test_get_team_roster_strength_unknown_team_not_found(mock_close_db, mock_get_db, client):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con

    response = client.get("/api/teams/99999/roster-strength")
    assert response.status_code == 404


# A group whose best player is below the 50th percentile is a weakness,
# and that player's name is attached as best_player.
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
@patch("app.api.teams.current_app.open_resource")
def test_get_team_roster_strength_below_median_is_weakness(
    mock_open_resource, mock_close_db, mock_get_db, client
):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"level": 1, "city_id": 58739}
    mock_cursor.fetchall.return_value = [
        _roster_strength_row(
            group_code="1B", player_id=7, first_name="Ruben", last_name="Santana",
            war=0.5, league_percentile=49,
        ),
    ]
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."

    response = client.get("/api/teams/1/roster-strength")
    group = response.get_json()["groups"][0]
    assert group["classification"] == "weakness"
    assert group["best_player"] == {
        "player_id": 7, "first_name": "Ruben", "last_name": "Santana", "league_rank": 10,
    }


# A group with no rated player at all (the SQL's all-NULL placeholder
# row) is a weakness, not an error or a skipped group -- best_player is
# null, not a name.
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
@patch("app.api.teams.current_app.open_resource")
def test_get_team_roster_strength_no_player_is_weakness(
    mock_open_resource, mock_close_db, mock_get_db, client
):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"level": 1, "city_id": 58739}
    mock_cursor.fetchall.return_value = [
        _roster_strength_row(
            group_code="DH", player_id=None, first_name=None, last_name=None,
            war=None, league_percentile=None,
        ),
    ]
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."

    response = client.get("/api/teams/1/roster-strength")
    group = response.get_json()["groups"][0]
    assert group["classification"] == "weakness"
    assert group["best_war"] is None
    assert group["best_percentile"] is None
    assert group["best_player"] is None


# 2+ players at/above the 50th percentile makes a group a surplus, and
# both their names are listed in surplus_players, best (highest WAR)
# first.
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
@patch("app.api.teams.current_app.open_resource")
def test_get_team_roster_strength_two_or_more_at_median_is_surplus(
    mock_open_resource, mock_close_db, mock_get_db, client
):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"level": 1, "city_id": 58739}
    mock_cursor.fetchall.return_value = [
        _roster_strength_row(
            group_code="2B", player_id=1, first_name="Tommy", last_name="Troy",
            war=3.0, league_percentile=90,
        ),
        _roster_strength_row(
            group_code="2B", player_id=2, first_name="Kevin", last_name="McGonigle",
            war=2.0, league_percentile=70,
        ),
    ]
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."

    response = client.get("/api/teams/1/roster-strength")
    group = response.get_json()["groups"][0]
    assert group["classification"] == "surplus"
    assert [p["last_name"] for p in group["surplus_players"]] == ["Troy", "McGonigle"]


# At/above median but only one such player -- adequate, not a surplus.
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
@patch("app.api.teams.current_app.open_resource")
def test_get_team_roster_strength_single_average_player_is_neutral(
    mock_open_resource, mock_close_db, mock_get_db, client
):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"level": 1, "city_id": 58739}
    mock_cursor.fetchall.return_value = [
        _roster_strength_row(group_code="CF", war=1.5, league_percentile=55),
    ]
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."

    response = client.get("/api/teams/1/roster-strength")
    body = response.get_json()
    assert body["groups"][0]["classification"] == "neutral"


# league_percentile comes back from MariaDB's ROUND() as a numeric string
# (DECIMAL type) -- must be cast to a real int, not passed through as-is.
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
@patch("app.api.teams.current_app.open_resource")
def test_get_team_roster_strength_casts_decimal_percentile_to_int(
    mock_open_resource, mock_close_db, mock_get_db, client
):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"level": 1, "city_id": 58739}
    mock_cursor.fetchall.return_value = [
        _roster_strength_row(group_code="RF", war=2.0, league_percentile="60"),
    ]
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."

    response = client.get("/api/teams/1/roster-strength")
    body = response.get_json()
    assert body["groups"][0]["best_percentile"] == 60
    assert isinstance(body["groups"][0]["best_percentile"], int)


# A player below the median doesn't count toward surplus_players even if
# another player at the same group qualifies -- surplus_players is
# filtered to at-or-above-median players only, not every rostered player.
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
@patch("app.api.teams.current_app.open_resource")
def test_get_team_roster_strength_surplus_players_excludes_below_median(
    mock_open_resource, mock_close_db, mock_get_db, client
):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"level": 1, "city_id": 58739}
    mock_cursor.fetchall.return_value = [
        _roster_strength_row(
            group_code="3B", player_id=1, first_name="Above", last_name="Median",
            war=2.0, league_percentile=80,
        ),
        _roster_strength_row(
            group_code="3B", player_id=2, first_name="Below", last_name="Median",
            war=0.1, league_percentile=20,
        ),
    ]
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."

    response = client.get("/api/teams/1/roster-strength")
    group = response.get_json()["groups"][0]
    assert [p["last_name"] for p in group["surplus_players"]] == ["Median"]
    assert group["surplus_count"] == 1


# Each named player carries their own league-wide ordinal rank
# (league_rank), and the group carries the pool size that rank is out of
# (league_pool_size) -- same "#N of total" framing as the team power
# ranking widget (ticket 0079).
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
@patch("app.api.teams.current_app.open_resource")
def test_get_team_roster_strength_includes_league_rank(
    mock_open_resource, mock_close_db, mock_get_db, client
):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"level": 1, "city_id": 58739}
    mock_cursor.fetchall.return_value = [
        _roster_strength_row(
            group_code="SS", player_id=1, first_name="Jordan", last_name="Lawlar",
            war=3.3, league_percentile=88, league_rank=12, league_pool_size=99,
        ),
    ]
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."

    response = client.get("/api/teams/1/roster-strength")
    group = response.get_json()["groups"][0]
    assert group["best_player"]["league_rank"] == 12
    assert group["league_pool_size"] == 99
    assert group["surplus_players"][0]["league_rank"] == 12


# Groups are ordered per ROSTER_STRENGTH_GROUP_ORDER regardless of the
# order the SQL query happened to return them in.
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
@patch("app.api.teams.current_app.open_resource")
def test_get_team_roster_strength_orders_groups(
    mock_open_resource, mock_close_db, mock_get_db, client
):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"level": 1, "city_id": 58739}
    mock_cursor.fetchall.return_value = [
        # "XX" stands in for an unrecognized group_code (shouldn't happen
        # in practice -- get_team_roster_strength.sql only ever emits a
        # real batting position now that pitchers are excluded) -- checks
        # the defensive sort-last fallback rather than raising.
        _roster_strength_row(group_code="XX"),
        _roster_strength_row(group_code="C"),
        _roster_strength_row(group_code="SS"),
    ]
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."

    response = client.get("/api/teams/1/roster-strength")
    body = response.get_json()
    assert [g["group"] for g in body["groups"]] == ["C", "SS", "XX"]


def _contract_decisions_row(**overrides):
    # Same shape as get_player_contract_inputs.sql's row
    # (tests/api/test_players.py's _contract_row), plus the identity
    # fields get_team_contract_inputs.sql adds for a roster-wide query.
    row = {
        "player_id": 1,
        "first_name": "Alice",
        "last_name": "Ace",
        "age": 30,
        "prone_overall": None,
        "batting_war": 3.0,
        "pitching_war": None,
        "pitching_role": None,
        "mlb_service_years": 4,
        "current_year": 2,
        # years=3 (not 4): remaining_contract_years=1, leaving a genuine
        # discretionary arbitration-estimate year before free agency
        # (service 4+1=5 < FA_SERVICE_YEARS=6) -- see
        # test_players.py's _contract_row for why a fully-signed
        # remaining horizon (ticket 0082) would return no recommendation
        # here instead.
        "years": 3,
        "war_dollar_value": None,
        "recommendation_extend_threshold": None,
    }
    row.update({f"salary{i}": 0 for i in range(15)})
    row["salary1"] = 10_000_000
    row["salary2"] = 12_000_000
    row.update(overrides)
    return row


# Test GET /api/teams/<id>/contract-decisions - not an MLB team (level != 1)
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
def test_get_team_contract_decisions_non_mlb_team_not_found(mock_close_db, mock_get_db, client):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"level": 2, "city_id": 12345}
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con

    response = client.get("/api/teams/59/contract-decisions")
    assert response.status_code == 404


# Test GET /api/teams/<id>/contract-decisions - level=1 exhibition team
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
def test_get_team_contract_decisions_exhibition_team_not_found(mock_close_db, mock_get_db, client):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"level": 1, "city_id": 0}
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con

    response = client.get("/api/teams/31/contract-decisions")
    assert response.status_code == 404


# Test GET /api/teams/<id>/contract-decisions - unknown team_id
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
def test_get_team_contract_decisions_unknown_team_not_found(mock_close_db, mock_get_db, client):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con

    response = client.get("/api/teams/99999/contract-decisions")
    assert response.status_code == 404


# An arbitration-eligible player (mlb_service_years=4, within the
# 3<=years<6 window) is included with their recommendation and
# total_surplus.
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
@patch("app.api.teams.current_app.open_resource")
def test_get_team_contract_decisions_includes_arb_eligible_player(
    mock_open_resource, mock_close_db, mock_get_db, client
):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"level": 1, "city_id": 58739}
    mock_cursor.fetchall.return_value = [
        _contract_decisions_row(player_id=7, first_name="Ruben", last_name="Santana"),
    ]
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."

    response = client.get("/api/teams/1/contract-decisions")
    assert response.status_code == 200
    body = response.get_json()
    assert len(body["players"]) == 1
    player = body["players"][0]
    assert player["player_id"] == 7
    assert player["first_name"] == "Ruben"
    assert player["last_name"] == "Santana"
    assert "recommendation" in player
    assert "total_surplus" in player


# A pre-arb rookie (mlb_service_years=1) has no recommendation -- 0058's
# rule -- so doesn't appear in the list at all.
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
@patch("app.api.teams.current_app.open_resource")
def test_get_team_contract_decisions_excludes_pre_arb_player(
    mock_open_resource, mock_close_db, mock_get_db, client
):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"level": 1, "city_id": 58739}
    mock_cursor.fetchall.return_value = [
        _contract_decisions_row(mlb_service_years=1),
    ]
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."

    response = client.get("/api/teams/1/contract-decisions")
    assert response.get_json()["players"] == []


# A player already past free-agency service (mlb_service_years=8) also
# has no recommendation, same exclusion.
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
@patch("app.api.teams.current_app.open_resource")
def test_get_team_contract_decisions_excludes_past_free_agency_player(
    mock_open_resource, mock_close_db, mock_get_db, client
):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"level": 1, "city_id": 58739}
    mock_cursor.fetchall.return_value = [
        _contract_decisions_row(mlb_service_years=8),
    ]
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."

    response = client.get("/api/teams/1/contract-decisions")
    assert response.get_json()["players"] == []


# A player with no computable surplus value at all (OOTP's years=0/
# current_year=0 unsigned placeholder contract, and no service-time
# record) is excluded, not a crash.
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
@patch("app.api.teams.current_app.open_resource")
def test_get_team_contract_decisions_excludes_unavailable_player(
    mock_open_resource, mock_close_db, mock_get_db, client
):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"level": 1, "city_id": 58739}
    mock_cursor.fetchall.return_value = [
        _contract_decisions_row(years=0, current_year=0, mlb_service_years=None),
    ]
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."

    response = client.get("/api/teams/1/contract-decisions")
    assert response.status_code == 200
    assert response.get_json()["players"] == []


# Multiple roster players are filtered independently -- only the
# arb-eligible one survives.
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
@patch("app.api.teams.current_app.open_resource")
def test_get_team_contract_decisions_filters_independently_per_player(
    mock_open_resource, mock_close_db, mock_get_db, client
):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"level": 1, "city_id": 58739}
    mock_cursor.fetchall.return_value = [
        _contract_decisions_row(player_id=1, mlb_service_years=1),
        _contract_decisions_row(player_id=2, mlb_service_years=4),
        _contract_decisions_row(player_id=3, mlb_service_years=8),
    ]
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."

    response = client.get("/api/teams/1/contract-decisions")
    body = response.get_json()
    assert [p["player_id"] for p in body["players"]] == [2]


def _performance_delta_row(**overrides):
    row = {
        "player_id": 1,
        "first_name": "Alice",
        "last_name": "Ace",
        "actual_batting_war": 3.0,
        "actual_pitching_war": None,
        "projected_war": 1.0,
        "delta": 2.0,
    }
    row.update(overrides)
    return row


# Test GET /api/teams/<id>/performance-deltas - not an MLB team (level != 1)
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
def test_get_team_performance_deltas_non_mlb_team_not_found(mock_close_db, mock_get_db, client):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"level": 2, "city_id": 12345}
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con

    response = client.get("/api/teams/59/performance-deltas")
    assert response.status_code == 404


# Test GET /api/teams/<id>/performance-deltas - level=1 exhibition team
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
def test_get_team_performance_deltas_exhibition_team_not_found(mock_close_db, mock_get_db, client):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"level": 1, "city_id": 0}
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con

    response = client.get("/api/teams/31/performance-deltas")
    assert response.status_code == 404


# Test GET /api/teams/<id>/performance-deltas - unknown team_id
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
def test_get_team_performance_deltas_unknown_team_not_found(mock_close_db, mock_get_db, client):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con

    response = client.get("/api/teams/99999/performance-deltas")
    assert response.status_code == 404


# A delta at/above the notable threshold (1.0) is included, overperformer.
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
@patch("app.api.teams.current_app.open_resource")
def test_get_team_performance_deltas_includes_overperformer(
    mock_open_resource, mock_close_db, mock_get_db, client
):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"level": 1, "city_id": 58739}
    mock_cursor.fetchall.return_value = [
        _performance_delta_row(
            player_id=7, first_name="Ruben", last_name="Santana",
            actual_batting_war=3.0, projected_war=1.0, delta=2.0,
        ),
    ]
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."

    response = client.get("/api/teams/1/performance-deltas")
    assert response.status_code == 200
    body = response.get_json()
    assert len(body["players"]) == 1
    player = body["players"][0]
    assert player["player_id"] == 7
    assert player["actual_war"] == 3.0
    assert player["projected_war"] == 1.0
    assert player["delta"] == 2.0


# A negative delta at/beyond the threshold is included too, underperformer.
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
@patch("app.api.teams.current_app.open_resource")
def test_get_team_performance_deltas_includes_underperformer(
    mock_open_resource, mock_close_db, mock_get_db, client
):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"level": 1, "city_id": 58739}
    mock_cursor.fetchall.return_value = [
        _performance_delta_row(actual_batting_war=0.5, projected_war=2.0, delta=-1.5),
    ]
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."

    response = client.get("/api/teams/1/performance-deltas")
    body = response.get_json()
    assert len(body["players"]) == 1
    assert body["players"][0]["delta"] == -1.5


# A delta inside the notable threshold is excluded -- not every player
# with any nonzero delta should show up, only meaningfully large ones.
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
@patch("app.api.teams.current_app.open_resource")
def test_get_team_performance_deltas_excludes_small_delta(
    mock_open_resource, mock_close_db, mock_get_db, client
):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"level": 1, "city_id": 58739}
    mock_cursor.fetchall.return_value = [
        _performance_delta_row(actual_batting_war=1.2, projected_war=1.0, delta=0.2),
    ]
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."

    response = client.get("/api/teams/1/performance-deltas")
    assert response.get_json()["players"] == []


# Two-way players sum batting + pitching actual WAR into one actual_war
# figure, same convention as get_team_war_summary.sql.
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
@patch("app.api.teams.current_app.open_resource")
def test_get_team_performance_deltas_two_way_sums_actual_war(
    mock_open_resource, mock_close_db, mock_get_db, client
):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"level": 1, "city_id": 58739}
    mock_cursor.fetchall.return_value = [
        _performance_delta_row(
            actual_batting_war=1.5, actual_pitching_war=0.8, projected_war=0.3, delta=2.0,
        ),
    ]
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."

    response = client.get("/api/teams/1/performance-deltas")
    assert response.get_json()["players"][0]["actual_war"] == pytest.approx(2.3)


# Multiple players are filtered independently, order (delta descending,
# as the SQL already returns) is preserved through Python's filtering.
@patch("app.api.teams.get_db")
@patch("app.api.teams.close_db")
@patch("app.api.teams.current_app.open_resource")
def test_get_team_performance_deltas_preserves_sql_order(
    mock_open_resource, mock_close_db, mock_get_db, client
):
    mock_con = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = {"level": 1, "city_id": 58739}
    mock_cursor.fetchall.return_value = [
        _performance_delta_row(player_id=1, delta=3.0),
        _performance_delta_row(player_id=2, delta=1.1),
        _performance_delta_row(player_id=3, delta=0.1),  # excluded, below threshold
        _performance_delta_row(player_id=4, delta=-2.0),
    ]
    mock_con.cursor.return_value.__enter__.return_value = mock_cursor
    mock_get_db.return_value = mock_con
    mock_open_resource.return_value.__enter__.return_value.read.return_value = "SELECT ..."

    response = client.get("/api/teams/1/performance-deltas")
    body = response.get_json()
    assert [p["player_id"] for p in body["players"]] == [1, 2, 4]
