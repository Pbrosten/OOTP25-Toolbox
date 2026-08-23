import pytest

from app.player_projection.contract_value import (
    calculate_surplus_value,
    recommend_contract_action,
    WAR_DOLLAR_VALUE,
    FA_SERVICE_YEARS,
    MIN_SALARY,
    INJURY_MULTIPLIERS,
)


def make_contract(current_year, years, **salaries):
    """current_year is 0-indexed into salary0..salary14, matching real
    players_contract data -- current_year=0 is the contract's first/only
    year, not "year one" in a 1-indexed sense."""
    salary_fields = {f"salary{i}": 0 for i in range(15)}
    salary_fields.update(salaries)
    return {"current_year": current_year, "years": years, **salary_fields}


def test_already_free_agent_eligible_with_no_contract_returns_none():
    result = calculate_surplus_value(
        base_war=3.0, current_age=28, mlb_service_years=FA_SERVICE_YEARS, contract=None
    )
    assert result is None


def test_signed_contract_years_use_actual_salary():
    contract = make_contract(current_year=0, years=2, salary0=1_000_000, salary1=2_000_000)
    result = calculate_surplus_value(
        base_war=2.0, current_age=25, mlb_service_years=2, contract=contract
    )
    assert [yr["cost"] for yr in result["years"][:2]] == [1_000_000, 2_000_000]
    assert result["years"][0]["age"] == 25
    assert result["years"][1]["age"] == 26


def test_one_year_contract_in_its_only_season_uses_salary0():
    # Regression: current_year=0 on a years=1 contract is a player in the
    # single year of a freshly-signed one-year deal, not an expired
    # contract -- current_year is 0-indexed, not 1-indexed.
    contract = make_contract(current_year=0, years=1, salary0=11_400_000)
    result = calculate_surplus_value(
        base_war=5.4, current_age=25, mlb_service_years=4, contract=contract
    )
    assert result["years"][0]["cost"] == 11_400_000


def test_projection_stops_at_free_agency_with_no_contract():
    result = calculate_surplus_value(
        base_war=2.0, current_age=30, mlb_service_years=5, contract=None
    )
    # 1 year left before hitting FA_SERVICE_YEARS (5 -> 6)
    assert len(result["years"]) == 1


def test_pre_arb_years_use_min_salary():
    result = calculate_surplus_value(
        base_war=1.0, current_age=22, mlb_service_years=0, contract=None
    )
    # service years 0/1/2 are pre-arb; service year 3 (index 3) switches to
    # the arbitration curve.
    pre_arb_years = result["years"][:3]
    assert all(yr["cost"] == MIN_SALARY for yr in pre_arb_years)
    assert result["years"][3]["cost"] != MIN_SALARY


def test_arbitration_years_scale_with_market_value():
    result = calculate_surplus_value(
        base_war=3.0, current_age=26, mlb_service_years=3, contract=None
    )
    first_arb_year = result["years"][0]
    assert first_arb_year["cost"] == 0.40 * (3.0 * WAR_DOLLAR_VALUE)


def test_age_decline_applies_only_after_32():
    result = calculate_surplus_value(
        base_war=4.0, current_age=30, mlb_service_years=6, contract=make_contract(0, 6)
    )
    wars = [yr["war"] for yr in result["years"]]
    assert wars[0] == 4.0  # age 30, no decline
    assert wars[1] == 4.0  # age 31, no decline
    assert wars[2] == pytest.approx(3.75)  # age 32, slow decline starts


def test_arbitration_cost_never_decreases_from_prior_actual_salary():
    # Regression: a low-WAR arb-eligible player whose actual current-year
    # salary is well above what that year's WAR alone would justify --
    # projected future arb years must not fall below it. Modeled on a real
    # case: a 0.11 WAR pitcher's real $1,680,000 arb-1 salary, where
    # WAR-driven arb pct math alone would compute less than MIN_SALARY for
    # the following years.
    contract = make_contract(current_year=0, years=1, salary0=1_680_000)
    result = calculate_surplus_value(
        base_war=0.109, current_age=25, mlb_service_years=3, contract=contract
    )
    costs = [yr["cost"] for yr in result["years"]]
    assert costs[0] == 1_680_000
    assert all(costs[i] >= costs[i - 1] for i in range(1, len(costs)))
    assert costs[1] == 1_680_000  # would otherwise fall to MIN_SALARY


def test_arbitration_cost_can_still_rise_above_prior_salary():
    # The floor is a floor, not a cap -- a strong performer's arb estimate
    # should rise past their actual prior salary when the math supports it.
    contract = make_contract(current_year=0, years=1, salary0=1_000_000)
    result = calculate_surplus_value(
        base_war=3.0, current_age=25, mlb_service_years=3, contract=contract
    )
    assert result["years"][1]["cost"] > 1_000_000


def test_negative_surplus_is_not_floored():
    contract = make_contract(current_year=0, years=1, salary0=50_000_000)
    result = calculate_surplus_value(
        base_war=0.5, current_age=25, mlb_service_years=0, contract=contract
    )
    assert result["total_surplus"] < 0


# === injury-risk discount (ticket 0059) ===


def test_injury_discount_does_not_apply_to_year_zero():
    # Year 0's base_war is already PA/IP-discounted upstream by
    # BatterProjection/PitcherProjection -- applying the multiplier again
    # here would double-count.
    contract = make_contract(current_year=0, years=3, salary0=0, salary1=0, salary2=0)
    result = calculate_surplus_value(
        base_war=3.0, current_age=25, mlb_service_years=2, contract=contract,
        prone_overall=200, is_pitcher=False,
    )
    assert result["years"][0]["value"] == pytest.approx(3.0 * WAR_DOLLAR_VALUE)


def test_injury_discount_applies_to_future_years_for_batter():
    contract = make_contract(current_year=0, years=3, salary0=0, salary1=0, salary2=0)
    result = calculate_surplus_value(
        base_war=3.0, current_age=25, mlb_service_years=2, contract=contract,
        prone_overall=200, is_pitcher=False,
    )
    expected = 3.0 * WAR_DOLLAR_VALUE * INJURY_MULTIPLIERS["Wrecked"]["Batter"]
    assert result["years"][1]["value"] == pytest.approx(expected)


def test_injury_discount_does_not_compound_across_years():
    # current_age=25 keeps every projected year below AGE_DECLINE_SLOW_START
    # (32), so war/value would be flat across years but for the multiplier --
    # confirms the same multiplier is applied fresh each year, not raised to
    # increasing powers.
    contract = make_contract(
        current_year=0, years=5, salary0=0, salary1=0, salary2=0, salary3=0, salary4=0
    )
    result = calculate_surplus_value(
        base_war=4.0, current_age=25, mlb_service_years=2, contract=contract,
        prone_overall=200, is_pitcher=False,
    )
    multiplier = INJURY_MULTIPLIERS["Wrecked"]["Batter"]
    expected = 4.0 * WAR_DOLLAR_VALUE * multiplier
    assert result["years"][1]["value"] == pytest.approx(expected)
    assert result["years"][4]["value"] == pytest.approx(expected)


def test_injury_discount_missing_prone_overall_is_unaffected():
    contract = make_contract(current_year=0, years=2, salary0=0, salary1=0)
    result = calculate_surplus_value(
        base_war=3.0, current_age=25, mlb_service_years=2, contract=contract,
        prone_overall=None, is_pitcher=False,
    )
    assert result["years"][1]["value"] == pytest.approx(3.0 * WAR_DOLLAR_VALUE)


def test_injury_discount_uses_starter_multiplier_for_pitching_role_11():
    contract = make_contract(current_year=0, years=2, salary0=0, salary1=0)
    result = calculate_surplus_value(
        base_war=3.0, current_age=25, mlb_service_years=2, contract=contract,
        prone_overall=200, is_pitcher=True, pitching_role=11,
    )
    expected = 3.0 * WAR_DOLLAR_VALUE * INJURY_MULTIPLIERS["Wrecked"]["Starter"]
    assert result["years"][1]["value"] == pytest.approx(expected)


def test_injury_discount_uses_reliever_multiplier_for_pitching_role_12_and_13():
    contract = make_contract(current_year=0, years=2, salary0=0, salary1=0)
    for role in (12, 13):
        result = calculate_surplus_value(
            base_war=3.0, current_age=25, mlb_service_years=2, contract=contract,
            prone_overall=200, is_pitcher=True, pitching_role=role,
        )
        expected = 3.0 * WAR_DOLLAR_VALUE * INJURY_MULTIPLIERS["Wrecked"]["Reliever"]
        assert result["years"][1]["value"] == pytest.approx(expected)


def test_injury_discount_defaults_unknown_pitching_role_to_starter():
    contract = make_contract(current_year=0, years=2, salary0=0, salary1=0)
    result = calculate_surplus_value(
        base_war=3.0, current_age=25, mlb_service_years=2, contract=contract,
        prone_overall=200, is_pitcher=True, pitching_role=None,
    )
    expected = 3.0 * WAR_DOLLAR_VALUE * INJURY_MULTIPLIERS["Wrecked"]["Starter"]
    assert result["years"][1]["value"] == pytest.approx(expected)


def test_injury_discount_durable_player_is_materially_unaffected():
    contract = make_contract(current_year=0, years=2, salary0=0, salary1=0)
    normal = calculate_surplus_value(
        base_war=3.0, current_age=25, mlb_service_years=2, contract=contract,
        prone_overall=10, is_pitcher=False,
    )
    assert normal["years"][1]["value"] == pytest.approx(
        3.0 * WAR_DOLLAR_VALUE * INJURY_MULTIPLIERS["Durable"]["Batter"]
    )


# === recommend_contract_action (ticket 0058) ===


def test_recommend_expiring_positive_surplus_trade_before_fa():
    contract = make_contract(current_year=0, years=1, salary0=1_000_000)
    result = calculate_surplus_value(
        base_war=3.0, current_age=28, mlb_service_years=5, contract=contract
    )
    assert len(result["years"]) == 1  # confirms the "years <= 1" bucket
    assert recommend_contract_action(result) == "Trade before free agency"


def test_recommend_expiring_negative_surplus_let_walk():
    contract = make_contract(current_year=0, years=1, salary0=50_000_000)
    result = calculate_surplus_value(
        base_war=0.5, current_age=28, mlb_service_years=5, contract=contract
    )
    assert len(result["years"]) == 1
    assert recommend_contract_action(result) == "Let walk"


def test_recommend_strong_surplus_multiyear_extend():
    contract = make_contract(
        current_year=0, years=3, salary0=1_000_000, salary1=1_000_000, salary2=1_000_000
    )
    result = calculate_surplus_value(
        base_war=3.0, current_age=25, mlb_service_years=2, contract=contract
    )
    assert len(result["years"]) >= 2
    # mlb_service_years=2 is well short of free agency (6), so team
    # control -- and thus this player's projection -- extends past the
    # 3-year contract into arbitration-estimated years the team doesn't
    # have locked in yet (discretionary=True): a real "should we extend
    # him further" decision, unlike the fully-signed case below.
    assert result["years"][-1]["source"] != "contract"
    assert recommend_contract_action(result) == "Extend"


def test_recommend_strong_surplus_fully_signed_contract_no_recommendation():
    # Ticket 0082 fix, regression for the exact bug reported: a player
    # already extended for their *entire* projected horizon (every year
    # "contract"-sourced) was returning "Extend" purely off a high
    # average surplus -- wrong, since the team already made that
    # decision and there's nothing left to extend. mlb_service_years=8
    # (already past free-agency service) plus a contract exactly as long
    # as the projection horizon it produces means no year reverts to an
    # arbitration/pre-arb estimate.
    contract = make_contract(
        current_year=0, years=3, salary0=1_000_000, salary1=1_000_000, salary2=1_000_000
    )
    result = calculate_surplus_value(
        base_war=6.0, current_age=27, mlb_service_years=8, contract=contract
    )
    assert len(result["years"]) == 3
    assert all(yr["source"] == "contract" for yr in result["years"])
    assert recommend_contract_action(result) is None


def test_recommend_mild_surplus_multiyear_keep_short_term():
    contract = make_contract(
        current_year=0, years=3, salary0=7_000_000, salary1=7_000_000, salary2=7_000_000
    )
    result = calculate_surplus_value(
        base_war=1.0, current_age=25, mlb_service_years=2, contract=contract
    )
    assert len(result["years"]) >= 2
    assert recommend_contract_action(result) == "Keep short-term"


def test_recommend_negative_surplus_discretionary_year_non_tender():
    # No signed contract -- the upcoming year is a projected arbitration
    # estimate (source="arbitration"), which the team could walk away from.
    result = calculate_surplus_value(
        base_war=-1.0, current_age=25, mlb_service_years=3, contract=None
    )
    assert len(result["years"]) >= 2
    assert result["years"][0]["source"] == "arbitration"
    assert recommend_contract_action(result) == "Non-tender"


def test_recommend_negative_surplus_signed_current_year_still_non_tender():
    # Regression, modeled on a real case: a low-WAR arb-1 player already
    # signed for *this* season (years=1, current_year=0 -- years[0] is
    # "contract", already tendered) but whose following seasons revert to
    # projected arbitration estimates. The team can't walk away from this
    # year, but can still non-tender him afterward -- checking only
    # years[0] missed this and returned "Let walk" instead.
    contract = make_contract(current_year=0, years=1, salary0=1_680_000)
    result = calculate_surplus_value(
        base_war=0.109, current_age=25, mlb_service_years=3, contract=contract
    )
    assert result["years"][0]["source"] == "contract"
    assert result["years"][1]["source"] == "arbitration"
    assert recommend_contract_action(result) == "Non-tender"


def test_recommend_negative_surplus_fully_signed_contract_no_recommendation():
    # Ticket 0082 fix: every remaining projected year is already
    # "contract"-sourced (not discretionary) -- the team is stuck with
    # this albatross deal regardless of surplus sign, same as a
    # fully-signed *positive*-surplus player has nothing left to
    # "Extend." Previously returned "Let walk," which is nonsensical for
    # a player already locked into a signed contract -- the team can't
    # just let him walk.
    contract = make_contract(
        current_year=0, years=3, salary0=50_000_000, salary1=50_000_000, salary2=50_000_000
    )
    result = calculate_surplus_value(
        base_war=-1.0, current_age=25, mlb_service_years=10, contract=contract
    )
    assert len(result["years"]) >= 2
    assert all(yr["source"] == "contract" for yr in result["years"])
    assert recommend_contract_action(result) is None
