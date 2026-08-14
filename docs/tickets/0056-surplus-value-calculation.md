# 0056 — Surplus-value calculation module + API route

- **Tag:** feat
- **Status:** Open
- **Depends on:** [0053](0053-contract-service-time-schema.md), [0054](0054-contract-service-time-migration.md)
- **Blocks:** [0057](0057-surplus-value-frontend-display.md)

## 1. Problem

[0042](0042-contract-arbitration-analyzer.md)'s core ask — "should we pay
this player, and how much is he worth?" — needs an actual surplus-value
number per player: projected value over the years the team controls him,
minus what he's actually owed. 0042's Design choices settled the *inputs*
this needs (a placeholder $/WAR constant, `prone_overall` as the injury
proxy, current-ratings-only WAR with no age-blend at the rating level) but
not the calculation's own mechanics. This ticket resolves those, following
a design discussion that settled four open questions:

1. **WAR horizon shape.** Not flat — a slow decline starting at age 32,
   harsher after 35, with tunable slope coefficients.
2. **Control window.** Full years-of-control via `players_service_time`
   (not just the signed contract's own remaining years) — meaning years
   beyond the current deal need an assumed arbitration/pre-arb cost curve.
3. **Two-way players.** Skip them for v1 (matches
   [0028](0028-pitcher-run-value-war.md)'s precedent of never netting
   batting and pitching WAR into one number).
4. **$/WAR constant.** Derived from real data, not guessed — see below.

## 2. Design choices

- **$/WAR constant, derived from real data.** Queried the `TEST.lg` save
  (post [0053](0053-contract-service-time-schema.md)/[0054](0054-contract-service-time-migration.md)
  ingestion): joined each player's current-year `players_contract` salary
  (indexed by `current_year` into `salary0..salary14`) against their latest
  `players_run_value`/`players_pitching_run_value` `WAR`. Filtered to a
  "clearly market-rate" sample (salary ≥ $15M, WAR ≥ 1.5 — i.e. established
  players unlikely to be on a below-market extension or rookie-scale deal):
  54 players, median implied $/WAR = **$8,286,135**, mean $8,894,141. Median
  is in line with real-MLB $/WAR estimates, which is a reasonable sanity
  check even though this is an in-save economy. **Chosen: `WAR_DOLLAR_VALUE
  = 8_300_000`** (rounded), as a named constant — swap freely once a better
  estimate exists (e.g. once real in-save free-agent-market signings are
  ingested, per 0041/0042's shared Outstanding note on that gap).
- **Age-decline curve.** No existing age-curve infrastructure to reuse (0026
  skipped it entirely at the rating-projection level). This ticket adds one
  scoped specifically to *this* forward-looking calculation, not to
  `BatterProjection`/`PitcherProjection` themselves. Applied as an
  accumulated per-year-of-age deduction from the player's current projected
  WAR, not a deduction from a hypothetical peak — a player already past 32
  today keeps their current (already-observed) WAR as the year-0 baseline;
  the curve only discounts *future* years relative to today.
  **Chosen starting coefficients** (explicitly tunable — flagged in-code as
  a placeholder, per this ticket's own instruction to revisit against real
  generated data):
  - Age < 32: no decline.
  - Age 32-35 inclusive: -0.25 WAR/year, cumulative.
  - Age 36+: -0.75 WAR/year, cumulative.
  - No floor at 0 — a projected-negative-WAR year is a real, intended
    signal (drives "Non-tender"/"Let walk" once 0042's deferred
    recommendation-threshold ticket exists).
- **Years-of-control window and the cost curve beyond the signed contract.**
  Team control runs through the earlier of: the last year of the signed
  contract, or the year the player's projected MLB service time reaches
  free-agency eligibility. **Chosen constants** (real-MLB convention,
  explicitly flagged as an unverified assumption — OOTP's own FA-eligibility
  rule isn't ingested or confirmed against a real save):
  - `FA_SERVICE_YEARS = 6` — service years at which a player reaches free
    agency.
  - `ARB_ELIGIBLE_SERVICE_YEARS = 3` — service years at which arbitration
    eligibility begins.
  - For years covered by the signed contract: use its actual scheduled
    salary (`salary[current_year - 1 + y]`).
  - For years beyond the contract but still under control: if projected
    service < 3, assume `MIN_SALARY`; if ≥ 3, assume an arbitration
    estimate = `ARB_PCT_OF_MARKET[arb_year] * (year_WAR * WAR_DOLLAR_VALUE)`,
    using the standard real-MLB rule-of-thumb progression
    `[0.40, 0.60, 0.80]` for arb years 1/2/3+ (also flagged as an
    unverified simplification — real MLB's actual arbitration formula is
    far more involved, and OOTP's own arbitration mechanic isn't modeled at
    all here beyond `players_service_time.has_received_arbitration`, which
    this ticket doesn't yet use for anything).
  - `MIN_SALARY = 740_000` — not guessed: the modal floor value actually
    observed across `players_contract.salary0` in the real `TEST.lg` save
    (multiple players at exactly $740,000, next lowest a $60,000 outlier).
- **Two-way player detection.** A player counts as two-way if their latest
  `rating_id` has rows in *both* `players_run_value` and
  `players_pitching_run_value` with non-null `WAR`. **Chosen:** return "not
  available" for these players rather than picking or summing a WAR value —
  matches 0028's precedent. (In the real `TEST.lg` sample used for the
  $/WAR derivation above, zero of the 180 usable player-rows were two-way —
  a rare case in practice, not just in theory.)
- **No new table — computed at read time.** Unlike `BatterProjection`/
  `PitcherProjection`'s output (persisted per-heap into `*_run_value`),
  surplus value depends on `players_contract` (a current-state table, not
  heap-dated per 0053) combined with the *latest* rating's WAR. There's no
  meaningful "historical surplus value as of heap X" to persist — it's a
  point-in-time function of current contract + current projection, same
  shape as the existing percentile endpoints
  (`get_expected_value_percentiles`), which also compute at request time
  from already-stored data. **Chosen:** a plain calculation function, no
  new schema.
- **Missing-input handling.** No `players_contract` row (player never
  signed / genuinely unrostered), no `players_service_time` row, or no
  current-heap WAR at all → "not available", not an error. Matches
  `DevelopmentTrends`' precedent (0052) of representing "nothing to show
  yet" as a valid empty/unavailable response rather than a 4xx.

## 3. Approach

New module `backend/app/player_projection/contract_value.py`, parallel in
spirit to `batter.py`/`pitcher.py` but far smaller (no pickled rating
curves — every constant here is a scalar or short list, defined inline):

```python
WAR_DOLLAR_VALUE = 8_300_000

AGE_DECLINE_SLOW_START = 32   # inclusive
AGE_DECLINE_HARSH_START = 36  # inclusive
AGE_DECLINE_SLOW_PER_YEAR = 0.25
AGE_DECLINE_HARSH_PER_YEAR = 0.75

FA_SERVICE_YEARS = 6
ARB_ELIGIBLE_SERVICE_YEARS = 3
ARB_PCT_OF_MARKET = [0.40, 0.60, 0.80]  # arb year 1 / 2 / 3+
MIN_SALARY = 740_000

MAX_PROJECTION_YEARS = 15  # matches salary0..salary14's width, safety cap


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
    contract: dict with current_year, years, salary0..salary14 -- or None
    if the player has no signed contract on file.
    Returns a dict with year-by-year and total figures, or None if there's
    nothing usable to project (e.g. already at/past free agency with no
    contract).
    """
    remaining_contract_years = 0
    salaries = []
    if contract is not None:
        remaining_contract_years = max(0, contract["years"] - contract["current_year"] + 1)
        salaries = [contract[f"salary{i}"] for i in range(15)]

    years = []
    y = 0
    while y < MAX_PROJECTION_YEARS:
        projected_service = mlb_service_years + y
        under_contract = y < remaining_contract_years
        if not under_contract and projected_service >= FA_SERVICE_YEARS:
            break

        projected_age = current_age + y
        year_war = base_war - _age_decline(current_age, projected_age)
        year_value = year_war * WAR_DOLLAR_VALUE

        if under_contract:
            year_cost = salaries[contract["current_year"] - 1 + y]
        elif projected_service < ARB_ELIGIBLE_SERVICE_YEARS:
            year_cost = MIN_SALARY
        else:
            arb_year = projected_service - ARB_ELIGIBLE_SERVICE_YEARS
            pct = ARB_PCT_OF_MARKET[min(arb_year, len(ARB_PCT_OF_MARKET) - 1)]
            year_cost = max(MIN_SALARY, pct * year_value)

        years.append({
            "year_offset": y, "age": projected_age, "war": year_war,
            "value": year_value, "cost": year_cost, "surplus": year_value - year_cost,
        })
        y += 1

    if not years:
        return None

    return {
        "years": years,
        "total_value": sum(yr["value"] for yr in years),
        "total_cost": sum(yr["cost"] for yr in years),
        "total_surplus": sum(yr["surplus"] for yr in years),
    }
```

Query helper (new function, likely in `app/api/players.py` or a small
`app/db/sql_scripts/api/get_player_contract_inputs.sql`, following the
existing per-route inline-vs-`.sql`-file convention): fetch latest
`rating_id`, `players_run_value.WAR`/`players_pitching_run_value.WAR` for
it (detect two-way), `players.age`, `players_contract` row, and
`players_service_time.mlb_service_years`.

New route in `app/api/players.py`:

```python
@bp.route("/<int:player_id>/surplus-value", methods=["GET"])
def get_player_surplus_value(player_id):
    ...
    if two_way or base_war is None or (contract is None and service_time is None):
        return jsonify({"available": False})
    result = calculate_surplus_value(base_war, age, mlb_service_years, contract)
    if result is None:
        return jsonify({"available": False})
    return jsonify({"available": True, **result})
```

Verify against the real `TEST.lg` save on a throwaway DB (established
pattern from 0053-0055): spot-check a handful of well-known contract rows
(e.g. the $46M/3.64 WAR player from the $/WAR derivation sample above)
produce sane, explainable surplus numbers.

**Files involved:**
- `backend/app/player_projection/contract_value.py` (new)
- `backend/app/api/players.py` (modified — new route)
- `backend/app/db/sql_scripts/api/get_player_contract_inputs.sql` (new, if
  the query is non-trivial enough to warrant its own file per existing
  convention)
