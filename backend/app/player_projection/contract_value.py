# === Constants (ticket 0056) ===
# WAR_DOLLAR_VALUE: derived from real TEST.lg data -- median implied $/WAR
# across market-rate contracts (salary >= $15M, WAR >= 1.5, n=54). Swap once
# real in-save free-agent-market signings are ingested (see 0042/0041).
WAR_DOLLAR_VALUE = 8_300_000

# Age-decline curve: scoped to this forward-looking calculation only, not
# to BatterProjection/PitcherProjection's own rating projections (0026 left
# those without an age blend). Coefficients are placeholders -- tune against
# real generated data.
AGE_DECLINE_SLOW_START = 32  # inclusive
AGE_DECLINE_HARSH_START = 36  # inclusive
AGE_DECLINE_SLOW_PER_YEAR = 0.25
AGE_DECLINE_HARSH_PER_YEAR = 0.75

# Years-of-control window: real-MLB convention, unverified against OOTP's
# own (unmodeled) free-agency/arbitration rules.
FA_SERVICE_YEARS = 6
ARB_ELIGIBLE_SERVICE_YEARS = 3
ARB_PCT_OF_MARKET = [0.40, 0.60, 0.80]  # arb year 1 / 2 / 3+

# Modal salary floor actually observed in players_contract.salary0 (TEST.lg).
MIN_SALARY = 740_000

MAX_PROJECTION_YEARS = 15  # matches salary0..salary14's width, safety cap

# Recommendation threshold (ticket 0058): rounded from p70 (~$4.4M) of
# average-surplus-per-year across a curated cohort of real, meaningfully
# salaried TEST.lg contracts (years > 0, salary0 > $1,000,000, n=611) --
# deriving from the full player pool produced nonsense (this save has 259
# teams, so most rated players are organizational depth, not a projection
# bug). Tune against more data later.
RECOMMENDATION_EXTEND_THRESHOLD = 5_000_000


def _age_decline(from_age: int, to_age: int) -> float:
    """Cumulative WAR deduction from from_age (exclusive) to to_age (inclusive)."""
    total = 0.0
    for age in range(from_age + 1, to_age + 1):
        if age >= AGE_DECLINE_HARSH_START:
            total += AGE_DECLINE_HARSH_PER_YEAR
        elif age >= AGE_DECLINE_SLOW_START:
            total += AGE_DECLINE_SLOW_PER_YEAR
    return total


def calculate_surplus_value(base_war, current_age, mlb_service_years, contract):
    """
    contract: dict with current_year/years/salary0..salary14, or None if
    the player has no signed contract on file. Returns None if there's
    nothing to project (e.g. already past free-agency service with no
    contract), otherwise a dict with a year-by-year breakdown and totals.
    """
    # current_year is 0-indexed into salary0..salary14 (confirmed against
    # real players_contract data: a years=N contract's active salary slots
    # are exactly salary0..salary(N-1), and current_year ranges 0..N-1 --
    # NOT a 1-indexed "year number", which silently off-by-one'd both the
    # remaining-years count and the salary lookup (wrapped to salary[-1]
    # for current_year=0) until caught on a real 1-year, current_year=0
    # contract.
    remaining_contract_years = 0
    salaries = []
    if contract is not None:
        remaining_contract_years = max(0, contract["years"] - contract["current_year"])
        salaries = [contract[f"salary{i}"] for i in range(15)]

    years = []
    y = 0
    previous_cost = None  # real-MLB arbitration never awards a pay cut
    while y < MAX_PROJECTION_YEARS:
        projected_service = mlb_service_years + y
        under_contract = y < remaining_contract_years
        if not under_contract and projected_service >= FA_SERVICE_YEARS:
            break

        projected_age = current_age + y
        year_war = base_war - _age_decline(current_age, projected_age)
        year_value = year_war * WAR_DOLLAR_VALUE

        if under_contract:
            year_cost = salaries[contract["current_year"] + y]
            source = "contract"
        elif projected_service < ARB_ELIGIBLE_SERVICE_YEARS:
            year_cost = MIN_SALARY
            source = "pre_arb"
        else:
            arb_year = projected_service - ARB_ELIGIBLE_SERVICE_YEARS
            pct = ARB_PCT_OF_MARKET[min(arb_year, len(ARB_PCT_OF_MARKET) - 1)]
            year_cost = max(MIN_SALARY, pct * year_value)
            # Arbitration salaries only go up (or stay flat), never down --
            # carries forward from the player's actual prior-year salary
            # (signed-contract or a previous arb projection alike), not
            # just this year's own WAR-driven estimate.
            if previous_cost is not None:
                year_cost = max(year_cost, previous_cost)
            source = "arbitration"

        previous_cost = year_cost
        years.append(
            {
                "year_offset": y,
                "age": projected_age,
                "war": year_war,
                "value": year_value,
                "cost": year_cost,
                "surplus": year_value - year_cost,
                "source": source,
            }
        )
        y += 1

    if not years:
        return None

    return {
        "years": years,
        "total_value": sum(yr["value"] for yr in years),
        "total_cost": sum(yr["cost"] for yr in years),
        "total_surplus": sum(yr["surplus"] for yr in years),
    }


def recommend_contract_action(result):
    """
    result: calculate_surplus_value's return value (not None). Two-axis
    decision: years-of-control-remaining x average-surplus-per-year tier,
    with "guaranteed vs. discretionary" (is there any point in the horizon
    the team could walk away for free) gating Non-tender. Checks the whole
    horizon, not just years[0] -- years[0] is often already a signed,
    already-tendered season (e.g. a real years=1 arb-1 deal), which the
    team is committed to regardless; what actually makes "Non-tender" a
    live option is a *later* projected year reverting to an
    arbitration/pre-arb estimate once that signed year runs out. See
    ticket 0058.
    """
    years = result["years"]
    years_remaining = len(years)
    avg_surplus = result["total_surplus"] / years_remaining
    discretionary = any(yr["source"] != "contract" for yr in years)

    if years_remaining <= 1:
        return "Trade before free agency" if avg_surplus >= 0 else "Let walk"
    if avg_surplus >= RECOMMENDATION_EXTEND_THRESHOLD:
        return "Extend"
    if avg_surplus >= 0:
        return "Keep short-term"
    return "Non-tender" if discretionary else "Let walk"
