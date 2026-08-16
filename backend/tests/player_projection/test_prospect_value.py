import pytest

from app.player_projection.prospect_value import (
    HITTER_WAR_TO_FV,
    PITCHER_WAR_TO_FV,
    PROMOTION_READY_FV_FLOOR,
    RISK_TAG_HIGH_GAP,
    RISK_TAG_LOW_GAP,
    RISK_TAG_MODIFIERS,
    _war_to_fv,
    _fv_to_value,
    _risk_tag,
    _apply_risk_modifier,
    build_batter_talent_projection_input,
    build_pitcher_talent_projection_input,
    batter_projection_inputs_from_row,
    pitcher_projection_inputs_from_row,
    calculate_prospect_value_from_row,
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


# === _risk_tag (ticket 0072) ===


def test_risk_tag_large_gap_is_negative():
    assert _risk_tag(fv=70, current_fv=40) == "-"  # gap 30 >= RISK_TAG_HIGH_GAP
    assert _risk_tag(fv=60, current_fv=40) == "-"  # gap 20, exactly the boundary


def test_risk_tag_small_gap_is_positive():
    assert _risk_tag(fv=55, current_fv=50) == "+"  # gap 5, exactly the boundary
    assert _risk_tag(fv=50, current_fv=50) == "+"  # gap 0, already at ceiling
    assert _risk_tag(fv=45, current_fv=50) == "+"  # negative gap (current > ceiling)


def test_risk_tag_middle_gap_is_untagged():
    assert _risk_tag(fv=55, current_fv=40) is None  # gap 15, between the two thresholds


def test_risk_tag_thresholds_are_module_constants():
    # Guards against the boundary tests above silently drifting out of sync
    # if the thresholds are ever tuned.
    assert RISK_TAG_HIGH_GAP == 20
    assert RISK_TAG_LOW_GAP == 5


# === _apply_risk_modifier (ticket 0072 post-close correction) ===


def test_apply_risk_modifier_discounts_negative_tag():
    base = {"surplus_value": 100_000_000, "expected_war": 5.0, "star_odds": 50.0}
    result = _apply_risk_modifier(base, "-")
    assert result["surplus_value"] == round(100_000_000 * RISK_TAG_MODIFIERS["-"])
    assert result["star_odds"] == round(50.0 * RISK_TAG_MODIFIERS["-"], 1)
    # expected_war is a pure ceiling number -- never modified.
    assert result["expected_war"] == 5.0


def test_apply_risk_modifier_boosts_positive_tag():
    base = {"surplus_value": 100_000_000, "expected_war": 5.0, "star_odds": 50.0}
    result = _apply_risk_modifier(base, "+")
    assert result["surplus_value"] == round(100_000_000 * RISK_TAG_MODIFIERS["+"])
    assert result["star_odds"] == round(50.0 * RISK_TAG_MODIFIERS["+"], 1)


def test_apply_risk_modifier_untagged_is_unchanged():
    base = {"surplus_value": 100_000_000, "expected_war": 5.0, "star_odds": 50.0}
    assert _apply_risk_modifier(base, None) == base


def test_apply_risk_modifier_star_odds_capped_at_100():
    base = {"surplus_value": 195_000_000, "expected_war": 27.5, "star_odds": 95.0}
    result = _apply_risk_modifier(base, "+")  # 95.0 * 1.10 = 104.5, would exceed 100
    assert result["star_odds"] == 100.0


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


# === row-slicing wrappers (ticket 0075: promoted from app/api/prospects.py
# so app/db/projection.py's heap-processing step can share them) ===


def _wide_row(**overrides):
    """Matches get_prospects.sql's/get_prospect_value_inputs.sql's shared
    column shape (both SQL scripts select these same column names)."""
    row = {
        "player_id": 1, "position": "SS", "bats": "R",
        "birth_date": "2003-01-01", "prone_overall": 50,
        "rating_id": "R001", "rating_date": "2025-09-01",
        "bat_babip": 50, "bat_gap": 50, "bat_eye": 50, "bat_power": 50,
        "bat_strikeouts": 50,
        "bat_babip_talent": 70, "bat_gap_talent": 70, "bat_eye_talent": 70,
        "bat_power_talent": 70, "bat_strikeouts_talent": 70,
        "speed": 50, "steal": 50, "baserunning": 50,
        **{f"pos{i}": 50 for i in range(2, 10)},
        **{f"pos{i}_talent": 60 for i in range(2, 10)},
        "pitch_role": None, "pitch_stuff": None, "pitch_control": None,
        "pitch_pbabip": None, "pitch_hra": None, "pitch_stamina": None,
        "pitch_hold": None, "pitch_stuff_talent": None,
        "pitch_control_talent": None, "pitch_pbabip_talent": None,
        "pitch_hra_talent": None,
    }
    row.update(overrides)
    return row


def test_batter_projection_inputs_from_row_sources_correctly():
    talent_input, current_input = batter_projection_inputs_from_row(_wide_row())
    assert talent_input["babip"] == 70
    assert talent_input["pos6"] == 60
    assert talent_input["speed"] == 50  # no talent equivalent -- stays current
    assert current_input["babip"] == 50
    assert current_input["pos6"] == 50


def test_pitcher_projection_inputs_from_row_sources_correctly():
    row = _wide_row(
        position="P", pitch_role=11, pitch_stuff=50, pitch_control=50,
        pitch_pbabip=50, pitch_hra=50, pitch_stamina=45, pitch_hold=45,
        pitch_stuff_talent=65, pitch_control_talent=65,
        pitch_pbabip_talent=65, pitch_hra_talent=65,
    )
    talent_input, current_input = pitcher_projection_inputs_from_row(row)
    assert talent_input["stuff"] == 65
    assert talent_input["stamina"] == 45  # no talent equivalent -- stays current
    assert current_input["stuff"] == 50


def test_calculate_prospect_value_from_row_dispatches_by_position():
    hitter_result = calculate_prospect_value_from_row(_wide_row(position="SS"))
    assert hitter_result is not None
    assert "fv" in hitter_result

    pitcher_row = _wide_row(
        position="P", pitch_role=11, pitch_stuff=50, pitch_control=50,
        pitch_pbabip=50, pitch_hra=50, pitch_stamina=50, pitch_hold=50,
        pitch_stuff_talent=70, pitch_control_talent=70,
        pitch_pbabip_talent=70, pitch_hra_talent=70,
    )
    pitcher_result = calculate_prospect_value_from_row(pitcher_row)
    assert pitcher_result is not None
    assert "fv" in pitcher_result


def test_calculate_prospect_value_from_row_missing_pitching_row_is_none():
    # Real case found running update-db league-wide: a position='P' player
    # with no matching players_pitching row at this heap (pitch_role NULL
    # from the LEFT JOIN) -- must return None cleanly, not raise
    # PitcherProjection's "Unrecognized pitcher role" ValueError.
    row = _wide_row(position="P")  # pitch_role stays None (fixture default)
    assert calculate_prospect_value_from_row(row) is None


def test_calculate_prospect_value_from_row_missing_batting_row_is_none():
    # Real case found running update-db league-wide: a position player
    # with no matching players_batting and/or players_batting_talent row
    # at this heap -- must return None cleanly, not raise BatterProjection's
    # KeyError(None) (which stringifies to the unhelpful message "None").
    no_current = _wide_row(position="SS", bat_babip=None)
    assert calculate_prospect_value_from_row(no_current) is None

    no_talent = _wide_row(position="SS", bat_babip_talent=None)
    assert calculate_prospect_value_from_row(no_talent) is None


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


def test_calculate_hitter_prospect_value_includes_risk_tag():
    close_to_ceiling = calculate_hitter_prospect_value(_batter_input(50), _batter_input(50))
    assert close_to_ceiling["risk_tag"] == "+"

    far_from_ceiling = calculate_hitter_prospect_value(_batter_input(80), _batter_input(20))
    assert far_from_ceiling["risk_tag"] == "-"


def test_calculate_hitter_prospect_value_risk_tag_modifies_surplus_and_star_odds():
    close_to_ceiling = calculate_hitter_prospect_value(_batter_input(50), _batter_input(50))
    base = _fv_to_value(close_to_ceiling["fv"], "hitter")
    assert close_to_ceiling["risk_tag"] == "+"
    assert close_to_ceiling["surplus_value"] == round(base["surplus_value"] * RISK_TAG_MODIFIERS["+"])
    # expected_war is never modified -- stays the pure ceiling number.
    assert close_to_ceiling["expected_war"] == base["expected_war"]

    far_from_ceiling = calculate_hitter_prospect_value(_batter_input(80), _batter_input(20))
    base_far = _fv_to_value(far_from_ceiling["fv"], "hitter")
    assert far_from_ceiling["risk_tag"] == "-"
    assert far_from_ceiling["surplus_value"] == round(base_far["surplus_value"] * RISK_TAG_MODIFIERS["-"])


def test_calculate_pitcher_prospect_value_sp_returns_result():
    result = calculate_pitcher_prospect_value(
        _pitcher_input(60, role=11), _pitcher_input(60, role=11)
    )
    assert result is not None
    assert result["fv"] in {fv for _, fv in PITCHER_WAR_TO_FV}
    assert "surplus_value" in result


def test_calculate_pitcher_prospect_value_includes_risk_tag():
    close_to_ceiling = calculate_pitcher_prospect_value(
        _pitcher_input(50, role=11), _pitcher_input(50, role=11)
    )
    assert close_to_ceiling["risk_tag"] == "+"

    far_from_ceiling = calculate_pitcher_prospect_value(
        _pitcher_input(80, role=11), _pitcher_input(20, role=11)
    )
    assert far_from_ceiling["risk_tag"] == "-"


def test_calculate_pitcher_prospect_value_risk_tag_modifies_surplus_and_star_odds():
    far_from_ceiling = calculate_pitcher_prospect_value(
        _pitcher_input(80, role=11), _pitcher_input(20, role=11)
    )
    base_far = _fv_to_value(far_from_ceiling["fv"], "pitcher")
    assert far_from_ceiling["risk_tag"] == "-"
    assert far_from_ceiling["surplus_value"] == round(base_far["surplus_value"] * RISK_TAG_MODIFIERS["-"])
    assert far_from_ceiling["expected_war"] == base_far["expected_war"]


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
