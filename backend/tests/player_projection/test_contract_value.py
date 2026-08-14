import pytest

from app.player_projection.contract_value import (
    calculate_surplus_value,
    WAR_DOLLAR_VALUE,
    FA_SERVICE_YEARS,
    MIN_SALARY,
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
