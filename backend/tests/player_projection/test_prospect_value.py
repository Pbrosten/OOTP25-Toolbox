import pytest

from app.player_projection.prospect_value import (
    HITTER_WAR_TO_FV,
    PITCHER_WAR_TO_FV,
    PROMOTION_READY_FV_FLOOR,
    _war_to_fv,
    _fv_to_value,
    build_batter_talent_projection_input,
    build_pitcher_talent_projection_input,
    calculate_hitter_prospect_value,
    calculate_pitcher_prospect_value,
)


# === _war_to_fv (pure bucket lookup, no projection math) ===


@pytest.mark.parametrize(
    "war,expected_fv",
    [
        (10.0, 80),   # well above the 7.0 "top" boundary
        (7.01, 80),
        (7.0, 70),    # 80 is strictly '>' 7.0, so exactly 7.0 falls to 70
        (5.0, 70),
        (4.99, 60),
        (3.4, 60),
        (2.5, 55),
        (1.6, 50),
        (0.8, 45),
        (0.0, 40),
        (-0.1, 30),
        (-50.0, 30),  # no lower bound -- always resolves, never None
    ],
)
def test_war_to_fv_hitter_boundaries(war, expected_fv):
    assert _war_to_fv(war, HITTER_WAR_TO_FV) == expected_fv


@pytest.mark.parametrize(
    "war,expected_fv",
    [
        (7.01, 80),
        (5.0, 70),
        (3.5, 60),
        (2.6, 55),
        (1.8, 50),
        (1.0, 45),
        (0.0, 40),
        (-0.1, 30),
    ],
)
def test_war_to_fv_pitcher_boundaries(war, expected_fv):
    assert _war_to_fv(war, PITCHER_WAR_TO_FV) == expected_fv


# === _fv_to_value ===


def test_fv_to_value_known_tier():
    assert _fv_to_value(60, "hitter") == {
        "surplus_value": 82_000_000, "expected_war": 12.5, "star_odds": 33.0,
    }
    assert _fv_to_value(60, "pitcher") == {
        "surplus_value": 70_000_000, "expected_war": 11.0, "star_odds": 21.0,
    }


def test_fv_to_value_fv80_falls_back_to_fv70_row():
    assert _fv_to_value(80, "hitter") == _fv_to_value(70, "hitter")
    assert _fv_to_value(80, "pitcher") == _fv_to_value(70, "pitcher")


def test_fv_to_value_below_35_is_zero():
    assert _fv_to_value(30, "hitter") == {
        "surplus_value": 0, "expected_war": 0.0, "star_odds": 0.0,
    }
    assert _fv_to_value(20, "pitcher") == {
        "surplus_value": 0, "expected_war": 0.0, "star_odds": 0.0,
    }


# === input builders ===


def test_build_batter_talent_input_sources_correctly():
    player_row = {
        "player_id": "p1", "birth_date": "2003-01-01", "position": "SS",
        "bats": "R", "prone_overall": 50,
    }
    rating_row = {"rating_id": "R001", "rating_date": "2025-09-01"}
    batting_talent_row = {
        "babip": 60, "gap": 60, "eye": 60, "power": 60, "strikeouts": 60,
    }
    basepath_row = {"speed": 45, "steal": 45, "baserunning": 45}
    fielding_position_talent_row = {
        f"pos{i}": 55 for i in range(2, 10)
    }

    result = build_batter_talent_projection_input(
        player_row, rating_row, batting_talent_row, basepath_row,
        fielding_position_talent_row,
    )

    # Developing categories come from the talent row.
    assert result["babip"] == 60
    assert result["power"] == 60
    assert result["pos6"] == 55
    # Non-developing categories stay current (no talent equivalent exists).
    assert result["speed"] == 45
    assert result["baserunning"] == 45
    # Passthrough identity fields.
    assert result["player_id"] == "p1"
    assert result["rating_id"] == "R001"


def test_build_pitcher_talent_input_sources_correctly():
    player_row = {"prone_overall": 50}
    rating_row = {"rating_id": "R001"}
    pitching_row = {"role": 11, "stamina": 45, "hold": 45}
    pitching_talent_row = {
        "stuff": 65, "control": 65, "pbabip": 65, "hra": 65,
    }

    result = build_pitcher_talent_projection_input(
        player_row, rating_row, pitching_row, pitching_talent_row,
    )

    assert result["stuff"] == 65
    assert result["control"] == 65
    # role/stamina/hold have no talent equivalent -- stay current.
    assert result["role"] == 11
    assert result["stamina"] == 45
    assert result["hold"] == 45


# === end-to-end wiring (real BatterProjection/PitcherProjection) ===


def _batter_input(rating, **overrides):
    data = {
        "player_id": "test_player", "rating_id": "R001",
        "rating_date": "2025-09-01", "birth_date": "2005-01-01",
        "position": "SS", "bats": "R", "prone_overall": 50,
        "babip": rating, "gap": rating, "eye": rating, "power": rating,
        "strikeouts": rating, "speed": rating, "steal": rating,
        "baserunning": rating,
        **{f"pos{i}": rating for i in range(2, 10)},
    }
    data.update(overrides)
    return data


def _pitcher_input(rating, role=11, **overrides):
    data = {
        "rating_id": "R001", "role": role, "stuff": rating,
        "control": rating, "pbabip": rating, "hra": rating,
        "stamina": rating, "hold": rating, "prone_overall": 50,
    }
    data.update(overrides)
    return data


def test_calculate_hitter_prospect_value_high_talent_beats_low_talent():
    weak = calculate_hitter_prospect_value(_batter_input(30), _batter_input(30))
    elite = calculate_hitter_prospect_value(_batter_input(80), _batter_input(80))
    assert elite["talent_war"] > weak["talent_war"]
    assert elite["fv"] >= weak["fv"]
    assert elite["surplus_value"] >= weak["surplus_value"]


def test_calculate_hitter_prospect_value_missing_input_is_none():
    assert calculate_hitter_prospect_value(None, _batter_input(50)) is None
    assert calculate_hitter_prospect_value(_batter_input(50), None) is None


def test_calculate_hitter_prospect_value_promotion_ready_flag():
    result = calculate_hitter_prospect_value(_batter_input(80), _batter_input(80))
    assert result["current_fv"] >= PROMOTION_READY_FV_FLOOR
    assert result["mlb_promotion_ready"] is True


def test_calculate_pitcher_prospect_value_sp_returns_result():
    result = calculate_pitcher_prospect_value(
        _pitcher_input(60, role=11), _pitcher_input(60, role=11)
    )
    assert result is not None
    assert result["fv"] in {fv for _, fv in PITCHER_WAR_TO_FV}
    assert "surplus_value" in result


@pytest.mark.parametrize("role", [12, 13])
def test_calculate_pitcher_prospect_value_rp_returns_result(role):
    # RP is no longer excluded (ticket 0068 post-close correction, user
    # request) -- their own smaller workload baseline penalizes them
    # naturally rather than needing a hard exclusion.
    result = calculate_pitcher_prospect_value(
        _pitcher_input(80, role=role), _pitcher_input(80, role=role)
    )
    assert result is not None
    assert "surplus_value" in result


def test_calculate_pitcher_prospect_value_rp_produces_lower_war_than_sp_at_same_ratings():
    sp = calculate_pitcher_prospect_value(
        _pitcher_input(60, role=11), _pitcher_input(60, role=11)
    )
    rp = calculate_pitcher_prospect_value(
        _pitcher_input(60, role=12), _pitcher_input(60, role=12)
    )
    assert rp["talent_war"] < sp["talent_war"]


def test_calculate_pitcher_prospect_value_missing_input_is_none():
    assert calculate_pitcher_prospect_value(None, _pitcher_input(50)) is None
    assert calculate_pitcher_prospect_value(_pitcher_input(50), None) is None
