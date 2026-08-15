# 0066 — Recalibrate run-value constants against this save's own league, not a fixed real-MLB baseline

- **Tag:** fix
- **Status:** Open
- **Depends on:** —
- **Blocks:** —

## 1. Problem

Reported directly: Kyle Manzardo (player 45014, active MLB roster, White
Sox) shows a *negative* Batting Run Value (-2.9) alongside a *73rd*
percentile — a below-average raw number reading as a well-above-average
percentile bar, which looks like a bug.

Investigated against the live `TEST.lg` save. The percentile calculation
itself is correct and its cohort isn't polluted by the administratively-
parked-player contamination [0064](0064-roster-depth-chart-frontend.md)
found and fixed elsewhere (verified: `get_player_expected_value_
percentiles.sql`'s cohort for Manzardo's rating snapshot is 607 players,
all with `is_active = 1` on `players_service_time` — zero parked/inactive
contamination). `440/607` of that cohort have `batting_runs` below
Manzardo's -2.9, giving exactly `73%` — the displayed number is the
correct percentile of the correct cohort.

**The real cause:** `batting_runs` (`app/player_projection/batter.py:226`,
`wRAA = ((wOBA - LG_WOBA) / FACTOR_WOBA) * PA`) is computed against
`LG_WOBA = 0.325`, a **fixed constant sourced from the real-MLB rate
tables the projection methodology's source spreadsheet was built from**
— not this save's own league average, despite "wRAA" (weighted Runs
*Above Average*) meaning "above the player's own league's average" by
definition in real sabermetrics. Confirmed via real data: the median
`batting_runs` among this save's actual active-roster MLB position
players (607 players, league_id 203, age ≥ 22, `is_active = 1` —
i.e. the real thing, not org depth) is **-9.14**, and only 123/607 (20%)
are non-negative. A below-real-MLB-average hitter can still be
well above-average *for this specific save's diluted talent pool* — this
save has 34 "MLB" teams (not the real 30), so per-team talent is more
diluted than a real MLB roster, a known finding from
[0058](0058-contract-recommendation-thresholds.md)'s investigation (259
teams total, most rated players are organizational depth) — this ticket
confirms the same dilution effect reaches even the genuinely active
26-man-roster population, not just unfiltered org depth. The percentile
(relative to this save's own population) and the raw value (relative to
real MLB) are each individually correct on their own terms, but
showing them side-by-side with no shared reference frame reads as
contradictory.

The identical pattern exists on the pitching side —
`pitcher.py`'s `pitching_runs` is computed from `LG_PWOBA = 0.327` and
`RA9_BASELINE = 4.65`, both likewise fixed real-MLB constants
(`pitcher.py:156-157`) — not reported directly, but the same root cause
applies symmetrically and should be fixed together.

**Chosen (confirmed with the user):** recalibrate the run-value baseline
constants to be derived from this save's own league-average performance
per heap, rather than hardcoded real-MLB numbers — the more correct fix,
not just a UI-level clarification, even though it's a bigger change (same
category of scope as [0026](0026-pitcher-projection-methodology.md)).

## 2. Design choices

- **Which constants get recalibrated.** `LG_WOBA` (batting) and
  `LG_PWOBA`/`RA9_BASELINE` (pitching) directly gate the symptom reported
  and are the most clearly-"should be league-relative by definition"
  constants (`wRAA`/`runs_prevented`'s own formulas are defined in terms
  of a league average). `RUNS_WIN` (batting, fixed at 9.92) and the
  pitching side's already-dynamic runs/win blend
  (`RUNS_PER_WIN_FULL_GAME_IP`/`OFFSET`/`SCALE`, ticket 0028) only scale
  the *magnitude* of WAR uniformly — they don't affect relative
  rankings/percentiles at all, so recalibrating them doesn't address the
  reported symptom, though they'd remain inconsistent with the *rest* of
  the metric now being save-relative if left untouched. `HITTER_
  REPLACEMENT_RUNS`/`rep_per_ip` (replacement level) are a different
  concept from a league *average* and need their own derivation approach,
  not simply "this save's mean." **Outstanding:** exact scope — just
  `LG_WOBA`/`LG_PWOBA`/`RA9_BASELINE`, or all of the above — not decided
  here, resolve when started.
- **How the per-save league average gets computed and applied.**
  Options: (a) compute once per heap during `update-db`'s projection
  pass (`app/db/projection.py`) and store it (a new small table, or a
  config/constants row), so every player's projection in that heap uses
  the same freshly-derived baseline; (b) compute it live in the
  percentile/value queries themselves, at request time. **Leaning (a)**
  — matches how `BatterProjection`/`PitcherProjection` already run once
  per heap during ingestion (not per API request), and avoids repeatedly
  recomputing a league-wide aggregate on every page load — but not
  decided here.
- **Cohort the league average is computed over.** Presumably the same
  "real, active MLB roster" population this investigation already
  validated (`league_id = 203`, `is_active = 1` on `players_service_
  time`, ticket 0064's ingestion) rather than every rated player
  (which would reintroduce the org-depth dilution this ticket is trying
  to correct *for*, the wrong direction). **Outstanding:** confirm this
  exact cohort definition when started, and whether it should also
  exclude two-way players or apply an age floor the way existing
  percentile cohorts already do.
- **Ripple effects into already-calibrated downstream constants.**
  [0056](0056-surplus-value-calculation.md)'s `WAR_DOLLAR_VALUE`
  ($8.3M/WAR, derived from real `TEST.lg` contract data under the
  *current* fixed-constant WAR scale) and
  [0058](0058-contract-recommendation-thresholds.md)'s
  `RECOMMENDATION_EXTEND_THRESHOLD` ($5M/yr, derived from the *current*
  WAR distribution) both assume today's WAR scale. If the baseline
  constants change, WAR values shift, and both downstream constants
  likely need re-derivation against the new scale to stay meaningful.
  **Outstanding:** not scoped here — re-derive as a follow-up once this
  ticket's new baseline is in place and real WAR values under it can be
  observed, rather than guessing at the new distribution in advance.
- **Outstanding — does the promotion-candidate percentile
  ([0064](0064-roster-depth-chart-frontend.md)) need re-verification?**
  It's rank-based within a level, not tied to the absolute run-value
  scale, so it's likely unaffected — but worth a quick sanity check once
  this ships, not decided here.

## 3. Approach

Not scoped into concrete implementation steps yet — the Outstanding
questions above (which constants, compute-once-per-heap vs. live,
downstream re-derivation) need resolving first, following this project's
established pattern of asking before assuming design decisions on a
ticket this size, mirroring how [0026](0026-pitcher-projection-methodology.md)
and [0058](0058-contract-recommendation-thresholds.md) were both started
with an explicit design-question round rather than assumed.

**Files involved:** TBD once the Outstanding questions above are
resolved — likely `backend/app/player_projection/batter.py` and
`pitcher.py` (constants + how they're supplied), `backend/app/db/
projection.py` (if computed once per heap), a new schema/migration
addition (if the derived baseline needs storing), and downstream
re-derivation notes for `contract_value.py`'s `WAR_DOLLAR_VALUE`/
`RECOMMENDATION_EXTEND_THRESHOLD`.
