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

# Injury-risk discount (ticket 0059): the exact per-season availability
# multipliers BatterProjection/PitcherProjection already look up from
# injury_constants.pkl for the *current* season (batter.py:53-58,
# pitcher.py:62-70,104-105) -- reused here as plain constants rather than
# re-derived, since they're already this project's real answer to "how much
# does this durability category affect a season's value." Applied only to
# projected years beyond the current one (year_offset >= 1); year 0's
# base_war is BatterProjection/PitcherProjection's own output, already
# discounted by this same multiplier for the current season.
INJURY_MULTIPLIERS = {
    "Durable": {"Batter": 1.02, "Starter": 1.10, "Reliever": 1.03},
    "Normal": {"Batter": 1.00, "Starter": 1.00, "Reliever": 1.00},
    "Fragile": {"Batter": 0.99, "Starter": 0.89, "Reliever": 0.98},
    "Wrecked": {"Batter": 0.95, "Starter": 0.76, "Reliever": 0.86},
}

# staging.players_pitching.role: 11 = Starting Pitcher, 12 = Relief Pitcher,
# 13 = Closer (folded into Reliever, matching PitcherProjection's own
# ROLE_MAP in pitcher.py:49).
PITCHING_ROLE_MAP = {11: "Starter", 12: "Reliever", 13: "Reliever"}


def _injury_category(prone_overall: int) -> str:
    """Mirrors BatterProjection/PitcherProjection's inline bucketing
    (batter.py:53-58, pitcher.py:64-69) -- duplicated rather than shared,
    matching this project's existing per-file style for this small a block."""
    return (
        "Durable" if prone_overall < 25 else
        "Normal" if prone_overall < 125 else
        "Fragile" if prone_overall < 175 else
        "Wrecked"
    )


def _injury_multiplier(prone_overall, is_pitcher: bool, pitching_role) -> float:
    """prone_overall/pitching_role may be None (missing rating data) -- treat
    as Normal/no discount rather than failing the whole projection."""
    if prone_overall is None:
        return 1.0
    category = _injury_category(prone_overall)
    if is_pitcher:
        role = PITCHING_ROLE_MAP.get(pitching_role, "Starter")
    else:
        role = "Batter"
    return INJURY_MULTIPLIERS[category][role]


def _age_decline(from_age: int, to_age: int) -> float:
    """Cumulative WAR deduction from from_age (exclusive) to to_age (inclusive)."""
    total = 0.0
    for age in range(from_age + 1, to_age + 1):
        if age >= AGE_DECLINE_HARSH_START:
            total += AGE_DECLINE_HARSH_PER_YEAR
        elif age >= AGE_DECLINE_SLOW_START:
            total += AGE_DECLINE_SLOW_PER_YEAR
    return total


def calculate_surplus_value(
    base_war,
    current_age,
    mlb_service_years,
    contract,
    prone_overall=None,
    is_pitcher=False,
    pitching_role=None,
    war_dollar_value=None,
):
    """
    contract: dict with current_year/years/salary0..salary14, or None if
    the player has no signed contract on file. Returns None if there's
    nothing to project (e.g. already past free-agency service with no
    contract), otherwise a dict with a year-by-year breakdown and totals.

    prone_overall/is_pitcher/pitching_role (ticket 0059): drive the
    injury-risk discount applied to years beyond the current one -- see
    INJURY_MULTIPLIERS. prone_overall=None (missing rating data) applies no
    discount.

    war_dollar_value (ticket 0066): this save's own recalibrated $/WAR
    (app/db/update.py::compute_market_constants, re-derived once per long
    heap from real players_contract data), falling back to the hardcoded
    WAR_DOLLAR_VALUE module constant when None -- same fallback shape as
    BatterProjection/PitcherProjection's data.get('lg_woba') pattern.
    """
    war_dollar_value = war_dollar_value if war_dollar_value is not None else WAR_DOLLAR_VALUE
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
        year_value = year_war * war_dollar_value
        if y >= 1:
            year_value *= _injury_multiplier(prone_overall, is_pitcher, pitching_role)

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


def compute_surplus_value_and_recommendation(row):
    """
    Shared by GET /api/players/<id>/surplus-value (ticket 0056/0058) and
    GET /api/teams/<id>/contract-decisions (ticket 0082) -- both need the
    same "row from get_player_contract_inputs.sql (or its team-scoped
    counterpart, get_team_contract_inputs.sql) -> surplus-value
    breakdown, plus a recommendation label if the player is currently
    arbitration-eligible" logic; factored out here so the second caller
    doesn't duplicate it.

    row: dict with age, prone_overall, batting_war, pitching_war,
    pitching_role, mlb_service_years, current_year/years/salary0..14,
    war_dollar_value, recommendation_extend_threshold (same shape both
    SQL scripts return).

    Returns None if there's nothing to project (no current WAR, or
    neither a contract nor a service-time record on file) -- the "not
    available" case. Otherwise, calculate_surplus_value's result dict,
    plus a "recommendation" key only when mlb_service_years currently
    falls in the arbitration window (ARB_ELIGIBLE_SERVICE_YEARS <= years
    < FA_SERVICE_YEARS) -- a player outside that window still gets their
    full surplus-value breakdown back, just without a recommendation
    label (ticket 0058's original behavior, unchanged by this refactor).

    A two-way player's batting and pitching WAR are summed into a single
    base_war for the whole projection (per user request) -- a deliberate
    change from 0056's original "exclude two-way players entirely"
    precedent, scoped to this calculation.
    """
    batting_war = row["batting_war"]
    pitching_war = row["pitching_war"]
    is_twp = batting_war is not None and pitching_war is not None
    if is_twp:
        base_war = batting_war + pitching_war
    else:
        base_war = batting_war if batting_war is not None else pitching_war

    # years=0/current_year=0 is a real row OOTP writes for every unsigned
    # player (a placeholder, not a 1-year $0 contract) --
    # current_year=0 would also wrap Python's salaries[-1] indexing in
    # calculate_surplus_value, so this must be filtered here, not just
    # treated as "no row".
    has_contract = row["years"] is not None and row["years"] > 0
    has_service_time = row["mlb_service_years"] is not None

    if base_war is None or row["age"] is None or not (has_contract or has_service_time):
        return None

    mlb_service_years = row["mlb_service_years"] or 0
    result = calculate_surplus_value(
        base_war=base_war,
        current_age=row["age"],
        mlb_service_years=mlb_service_years,
        contract=row if has_contract else None,
        prone_overall=row["prone_overall"],
        # A TWP's injury-durability lookup uses the batter multiplier, not
        # the pitcher one -- their primary defensive workload (games
        # played/batted) is typically far larger than their pitching
        # innings share, so is_pitcher is only True for a player who is a
        # pitcher and *not* also a hitter.
        is_pitcher=pitching_war is not None and batting_war is None,
        pitching_role=row["pitching_role"],
        war_dollar_value=row["war_dollar_value"],
    )
    if result is None:
        return None

    # Recommendation labels only apply to a player's current
    # arbitration-eligibility window -- pre-arb rookies and players
    # already past free-agency service (whether on a long-term deal or
    # otherwise) aren't the "should we tender/extend/non-tender him"
    # decision this label set describes (ticket 0058, per user report).
    if ARB_ELIGIBLE_SERVICE_YEARS <= mlb_service_years < FA_SERVICE_YEARS:
        recommendation = recommend_contract_action(
            result, recommendation_extend_threshold=row["recommendation_extend_threshold"]
        )
        # recommend_contract_action returns None when the player is
        # already fully extended through their whole projected horizon
        # (ticket 0082 fix) -- no "recommendation" key at all in that
        # case, same absent-key convention as the pre-arb/post-FA cases
        # above, not a null value.
        if recommendation is not None:
            result = {**result, "recommendation": recommendation}

    return result


def recommend_contract_action(result, recommendation_extend_threshold=None):
    """
    result: calculate_surplus_value's return value (not None). Two-axis
    decision: years-of-control-remaining x average-surplus-per-year tier,
    with "guaranteed vs. discretionary" (is there any point in the horizon
    the team could walk away for free) gating both Non-tender and
    "Extend"/"Keep short-term" entirely. Checks the whole horizon, not
    just years[0] -- years[0] is often already a signed, already-tendered
    season (e.g. a real years=1 arb-1 deal), which the team is committed
    to regardless. See ticket 0058.

    Returns None -- no live decision -- when every remaining projected
    year is already locked in under a signed contract (ticket 0082
    fix): a player already extended for their whole relevant horizon has
    nothing left to extend, no matter how large their surplus value is.
    The bug this fixed: a fully-extended star with high projected surplus
    (e.g. a real 7-year, all-"contract"-sourced deal) was returning
    "Extend" -- confusing/wrong, since the team already made that exact
    decision and there's no action left to take. Discretionary (at least
    one remaining year *not* already under contract, i.e. relies on an
    arbitration/pre-arb estimate) is what actually makes any of
    Extend/Keep short-term/Non-tender a live option -- once discretionary
    is True, "Non-tender" specifically needs a later year to *revert* to
    a non-contract estimate after an earlier signed year runs out, not
    just any non-contract year.

    recommendation_extend_threshold (ticket 0066): this save's own
    recalibrated $/yr cutoff (app/db/update.py::compute_market_constants),
    falling back to the hardcoded RECOMMENDATION_EXTEND_THRESHOLD module
    constant when None.
    """
    recommendation_extend_threshold = (
        recommendation_extend_threshold
        if recommendation_extend_threshold is not None
        else RECOMMENDATION_EXTEND_THRESHOLD
    )

    years = result["years"]
    years_remaining = len(years)
    avg_surplus = result["total_surplus"] / years_remaining
    discretionary = any(yr["source"] != "contract" for yr in years)

    if years_remaining <= 1:
        return "Trade before free agency" if avg_surplus >= 0 else "Let walk"
    if not discretionary:
        return None
    if avg_surplus >= recommendation_extend_threshold:
        return "Extend"
    if avg_surplus >= 0:
        return "Keep short-term"
    return "Non-tender"
