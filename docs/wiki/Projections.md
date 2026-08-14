# Projections (Developer Reference)

[← Back to Home](Home.md)

This page documents the *methodology* behind expected-stat projections — how
a 20-80 scouting rating turns into a projected AVG/wOBA/ERA/etc, plus a
run-value/WAR figure. Both are now implemented for both player types:
batters in `backend/app/player_projection/batter.py`, pitchers in
`backend/app/player_projection/pitcher.py` (see
[docs/tickets/0015](../tickets/0015-pitcher-projection-epic.md) and its
breakdown, 0024–0028; the pitcher implementation deliberately diverges from
§3.2's age-development track (0026, see §3.6) and omits a reliever-leverage
WAR adjustment (0028, see §3.7)). This page was originally written to pin
down the pitcher methodology before that implementation work started, from
the same source spreadsheet as the batter methodology; it's kept as the
design record and confirmed/open tracker.

Both methodologies originate from the same source workbook:
[`docs/resources/OOTP calculator blank.xlsx`](../resources/OOTP%20calculator%20blank.xlsx)
("Position Players" / "Starting Pitchers" / "Relief Pitchers" tabs, plus
"Weighting Constants" / "Projection Constants" / "Development Constants" for
the lookup tables). Cell references below (`R3`, `'Projection Constants'!$Y$7:$Y$23`,
etc.) are to that workbook, so the formulas can be re-verified directly
against it rather than taken on faith from this doc.

## 1. Shared shape

Both methodologies follow the same three-stage shape:

1. **Baseline** — plug 20-80 ratings into a rating→rate lookup table (a
   piecewise curve keyed on the 20-80 scale, e.g. "a 55 Stuff rating implies
   a 0.221 strikeout rate") to get counting stats at a **fixed, arbitrary
   workload** (e.g. 550 AB for a batter, 900 AB-equivalent for a starting
   pitcher). This fixed workload exists purely so the rate lookups have a
   concrete number to multiply against — it is *not* the player's projected
   playing time.
2. **Scaling** — compute the player's *actual* expected playing time (PA for
   batters; PA/IP for pitchers) from position/role/durability/stamina
   factors, then rescale every baseline counting stat by
   `actual_workload / baseline_workload`, preserving the baseline's rates
   while matching real workload.
3. **Rates** — derive AVG/OBP/wOBA (and for pitchers, RA/9/ERA) from the
   scaled counting stats.

Batters implement this as one combined `pa_factor`
(`backend/app/player_projection/batter.py:185-196`,
`calc_offensive_stats_base()` + `calc_offensive_stats()`). The pitcher
spreadsheet keeps the two workload numbers as separate named quantities
(baseline `AB`/`PA` vs. target `PA`) and reconciles them with an explicit
ratio per stat — functionally the same idea, more spelled out.

Ratings feed all of this through **rating→rate lookup tables** ("Projection
Constants" sheet), not a closed-form equation — e.g. there's no formula for
"strikeout rate as a function of Stuff," just a table of `(rating value,
rate)` pairs for each 5-point rating step from 20 to 80, looked up via
`XLOOKUP`. Any code implementation needs the equivalent of a lookup table
(`batter.py` already does this via `offensive_constants.pkl` /
`defensive_constants.pkl` / `injury_constants.pkl`, loaded once at import
time — see `backend/app/player_projection/batter.py:9-15`).

## 2. Batter projection (implemented, for comparison)

`BatterProjection` (`backend/app/player_projection/batter.py`):

- Fixed baseline: `AB = 550` (`offensive_stats` default, line 91).
- Rating→rate lookups (`lookup_bat`): `gap`→XBH rate, `speed`→3B share,
  `power`→HR rate, `strikeouts`→K rate, `eye`→BB rate, `babip`→1B rate —
  `calc_offensive_stats_base()`, lines 160-178.
- Actual workload: `def_pos_adj[position]['PA']` (a fixed PA figure per
  position, lines 30-39) divided by an injury/durability multiplier
  (`lookup_inj`, keyed off the `Prone` rating bucketed into
  Durable/Normal/Fragile/Wrecked) — `pa_factor`, lines 187-188.
- Every counting stat is rescaled by `pa_factor` (and a small DH `hit_factor`
  penalty), lines 190-195.
- Rates (`calc_offensive_rates`, lines 198-211) and run value/WAR
  (`calc_player_values`, lines 224-241) follow.

No manual "how much will this player play" input exists for batters — it's
entirely derived from `position` + the `Prone` durability rating. This
matters for §4 below, where the pitcher spreadsheet's equivalent turns out
to need one.

## 3. Pitcher projection methodology (implemented — production in 0026, value/WAR in 0028)

Both the "Starting Pitchers" and "Relief Pitchers" tabs compute three
parallel projection tracks per player — **Current**, **Projected**, and
**Peak** — that differ only in *which* rating feeds them (current actual,
age-developed, or full potential). This doc covers the **Projected**
track (`'Starting Pitchers'!CG:DA` / `'Relief Pitchers'!CH:DB`), since
that's the one analogous to what `players_batting_expected` stores today.

### 3.1 Rating inputs

From `staging.players_pitching` (see
[0024](../tickets/0024-pitcher-schema-ratings-tables.md)'s column inventory),
only the **overall** ratings are used for production math: `stuff`,
`control` (maps to the sheet's "Control", staging column
`pitching_ratings_overall_control`), `pbabip`, `hra` (sheet's "HRR" — HR
rate), plus `velocity`/`stamina` from the misc block. The `vsl`/`vsr` splits
and the 12 per-pitch-type grade columns are **not used anywhere** in this
methodology — confirms 0024's decision to leave them out of the schema.

### 3.2 Age/development adjustment (feeds the "Projected" track specifically)

Unlike Current (which uses `MAX(actual_current_rating, developed_rating)`)
or Peak (which uses raw Potential), the **Projected** track uses a
"developed-or-actual" rating: `IFS(age > 24, current_actual_rating, age <
25, smoothed_developed_rating)` (`'Starting Pitchers'!AW3:AZ3`, mirrored on
the RP tab at `AX3:BA3`). For a player 25 or older this is just their
current rating — the interesting part only applies to players under 25:

1. **Development Constants** sheet: a lookup table keyed on
   `(Age, Potential rating)` → developed current-year rating, one column
   each for Stuff/Control/pBABIP/HRR (columns H-K), covering ages 16-40ish
   × potential 20-80 in 5-point steps.
2. A makeup adjustment is added on top: `(Adaptability + WorkEthic +
   Intelligence) * (25 - age) / 9`, where each of the three categorical
   traits (`H`/`N`/`L` in the raw export) maps to `+1`/`0`/`-1`
   (`'Starting Pitchers'!AK3:AN3`). Only these three traits feed development
   — Loyalty and Financial-ambition don't. This term is zero once the player
   turns 25.
3. The result is rounded to the nearest 5 (`ROUND(x/5,0)*5`,
   `'Starting Pitchers'!AS3:AV3`) to stay on the same 20-80 grid the rate
   lookup tables use.

### 3.3 Baseline production

Fixed workload constants (`'Weighting Constants'!B24`/`B26`):

| | AB baseline | PA target | GS/G baseline | Replacement runs/IP |
|---|---|---|---|---|
| Starting Pitchers | 900 (`B24`) | 750 (`B25`) | 27 GS (`B38`) | 0.12 (`B41`) |
| Relief Pitchers | 300 (`B26`) | 300 (`B27`) | 50 G (`B39`) | 0.03 (`B42`) |

At the fixed AB baseline, each rating maps to a rate via
`'Projection Constants'!A7:A23` (the 20-80 grid) against a dedicated column
— **SP and RP use separate rate curves**, not the same table:

| Outcome | SP rating → column | RP rating → column |
|---|---|---|
| K rate | Stuff → `W` | Stuff → `AC` |
| HR rate | HRR → `X` | HRR → `AD` |
| Non-HR hit rate (of AB-HR-K) | pBABIP → `Y` | pBABIP → `AE` |
| BB rate | Control → `Z` | Control → `AF` |

(`'Starting Pitchers'!BG3:BK3` / `'Relief Pitchers'!BH3:BL3` for the formulas;
`HBP = AB * 0.009` — `'Weighting Constants'!B31` — is the one rate that
doesn't vary by rating.) Relievers get meaningfully better rate-per-rating
curves across the board (e.g. a 55 Stuff → 0.221 K/AB for a starter vs. 0.266
for a reliever) — this is the model's way of encoding that a short-relief
pitcher's stuff plays up.

### 3.4 Playing-time scaling

The actual target PA (`'Starting Pitchers'!CN3`, `'Relief Pitchers'!CO3`):

```
PA_target * XLOOKUP(stamina_rating, 'Projection Constants'!A7:A23, <TBF/G or TBF/GS column>)
          * Playing_Time_input
          * XLOOKUP(prone_category, 'Weighting Constants'!A2:A7, <SP or RP durability column>)
```

`Playing_Time_input` (`AJ` column) is a **manual, per-player 0-1ish share**
— e.g. "this pitcher gets a full rotation slot" vs. a swingman getting a
fraction. **This is filled in by hand in the spreadsheet and has no
equivalent anywhere in the OOTP ratings export.** Batters have no analogous
manual input (§2) — their workload is fully derived from position + Prone.
This is a real gap for an automated pipeline and needs a decision before
[0026](../tickets/0026-pitcher-projection-methodology.md) can be
implemented: candidates are defaulting everyone to 1.0 (loses the
rotation-share signal entirely), deriving a share from `role`/roster-slot
order in `staging.players_pitching`/`staging.players_roster_status`, or
punting it as a future manual override field. **Flagged as newly-discovered,
not resolved here.**

GS (starters) / G (relievers) uses the same three factors against a
different baseline constant (27 GS or 50 G) — same formula shape, see
`'Starting Pitchers'!CY3` / `'Relief Pitchers'!CZ3`.

Every baseline counting stat (§3.3) is then rescaled by
`actual_PA / baseline_PA` — e.g. `CP3 = CI3 * CN3 / CG3` for AB — same "ratio
scaling" idea as batters' `pa_factor`, just computed as an explicit ratio
per stat rather than one factor applied uniformly (numerically equivalent).

### 3.5 Rate stats

From the scaled counting stats (`PA, AB, H, HR, BB, HBP, K`):

- `BA = H / AB`
- `OBP = (H + BB + HBP) / PA`
- `wOBA_against = (0.7*(BB+HBP) + 1.0*(H-HR) + 2.0*HR) / PA` — the BB/HBP and
  HR weights (`'Weighting Constants'!B10` and `B14`, 0.7 and 2.0) are
  **identical to** `FACTOR_BB`/`FACTOR_HR` in `batter.py:20-24`. There's no
  batter-side equivalent of the third weight (`B15`, "non-HR hits" = 1.0):
  batters split hits into 1B/2B/3B with three different weights
  (0.9/1.25/1.6), but a pitcher's ratings don't carry batted-ball-type
  granularity, so every non-HR hit allowed gets the same flat weight.
- `IP = (PA - H - BB - HBP) / 2.91` — `'Weighting Constants'!B36`, a fixed
  outs-per-inning-equivalent divisor.
- `runs_prevented = (0.327 - wOBA_against) / 1.2 * PA` — a wRAA-style
  calculation (`'Weighting Constants'!B37` league pwOBA, `B34` wOBA scale)
  that is nominally part of the spreadsheet's *Value* section, not
  Production, but is unavoidable here:
  `RA/9 = 4.65 - runs_prevented / IP * 9` and `ERA = 0.92 * RA/9`
  (`'Weighting Constants'!B40` league-average RA/9, `B43` ERA/RA9 ratio) —
  RA/9/ERA can't be computed without it. **This one intermediate is included
  here because Production depends on it; the rest of the Value/WAR breakdown
  (BR runs, replacement runs, defensive runs, runs/win, WAR) is
  intentionally out of scope for this doc** — that's still an open question
  in [0026](../tickets/0026-pitcher-projection-methodology.md#2-design-choices).

### 3.6 What's confirmed vs. still open

**Confirmed by this spreadsheet analysis, and implemented in
`PitcherProjection` (0026):**

- Output stat set for `players_pitching_expected`: `PA, AB, H, HR, BB, HBP,
  K, BA, OBP, wOBA, IP, GS (SP only) / G (RP only), RA/9, ERA`.
- The rating→rate lookup table shape and exact constants (§3.3), split by
  role (SP vs. RP get different curves) — verified formula-for-formula
  against the source workbook (fed identical inputs through both
  `PitcherProjection` and the live spreadsheet; every output stat matched
  exactly).
- The "Playing Time" manual-input gap (§3.4) — resolved as a known
  limitation rather than a derivation: every pitcher gets a full share
  (`PLAYING_TIME_INPUT = 1.0` in `pitcher.py`), not derived from roster
  data. Overstates playing time for organizational depth/fringe arms.
- SP vs. RP role classification — `staging.players_pitching.role` is a
  numeric roster-role code, confirmed against real dump data (cross-checked
  against actual `GS`/`G` usage in `staging.players_career_pitching_stats`):
  `11` = Starting Pitcher, `12` = Relief Pitcher, `13` = Closer (small
  subset, all-relief usage, folded into the RP bucket since the spreadsheet
  has no third curve). Also discovered in the process:
  `staging.players_pitching` has one row per player in the *entire league*
  (~135k/heap), not just pitchers — non-pitchers get `role = 0` and are
  filtered out at both the migration layer (`migration_short.sql`'s
  `WHERE ... role IN (11, 12, 13)`) and defensively in `PitcherProjection`.

**Deliberately not implemented** (implementation choice, not new
methodology findings):

- The age-development pipeline for players under 25 (§3.2) — the formulas
  were confirmed, but `PitcherProjection` skips them and uses current
  ratings directly, matching how `BatterProjection` actually works today
  (no age/potential blending there either). The pitcher export is also
  missing one of the three makeup traits the blend needs (no Adaptability
  field), which would have required inventing a mapping to fill the gap.

**Still open**, deferred past 0026:

- Whether the "Current"/"Peak" tracks (not just "Projected") are ever
  needed — the app today only surfaces one expected-stat snapshot per rating
  date (`players_batting_expected` has no Current/Peak equivalent for
  batters either), so this doc assumes "Projected" is the only track that
  matters, but that wasn't an explicit product decision.

## 3.7 Pitcher value/WAR methodology (implemented, 0028)

Same "Projected Value" column block (`'Starting Pitchers'!DB:DH` /
`'Relief Pitchers'!DC:DI`) read through cell-by-cell, same rigor as §3.3-3.5.
Implemented in `PitcherProjection.calc_player_values()`
(`backend/app/player_projection/pitcher.py`), stored in
`players_pitching_run_value` — a parallel table to `players_run_value`, not
an extension of it (see [0028](../tickets/0028-pitcher-run-value-war.md#2-design-choices)
for why: `get_player_expected_value_percentiles.sql` already filters
`p.position != 'P'`, so the batting value table and its one consumer assume
"pitchers excluded" by contract, not just convention).

- **`pitching_runs`** — the wRAA-against term: `(lg_pwOBA - wOBA_against) /
  wOBA_scale * PA` (`'Weighting Constants'!B37`, `B34`). This is exactly
  `PitcherProjection.runs_prevented`, already computed in `calc_rates()` to
  derive RA/9 (§3.5) — `calc_player_values()` reuses the stashed attribute
  rather than recomputing it, per 0028's Design choices.
- **`baserunning_runs`** — `IP * XLOOKUP(Hold, 'Projection Constants'!$A$7:$A$23,
  $AB$7:$AB$23)`. The Hold→runs/IP curve is the one rate curve **shared by
  SP and RP** (both tabs' formulas point at the same `$AB$7:$AB$23` range),
  unlike the K/HR/H/BB curves which are role-specific — added to
  `pitching_constants.pkl` as an unprefixed `BR` column, looked up via
  `PitcherProjection.lookup_baserunning()`. `hold` was already a
  `players_pitching` column (0024) but unused until now; added to
  `get_pitcher_projection_inputs.sql`'s SELECT.
- **Replacement runs** — `IP * rep_per_ip`, where `rep_per_ip` is 0.12 (SP)
  / 0.03 (RP) (`'Weighting Constants'!B41`/`B42` — these were already
  documented in §3.3's baseline table, just unused until 0028).
  Computed and folded into `total_runs` but **not stored as its own column**,
  matching `players_run_value`'s precedent (`BatterProjection.calc_player_values()`
  computes `Replace_runs` but `players_run_value` has no `replacement_runs`
  column either — see `batter.py:236`, `projection.py`'s `"value"` INSERT).
- **Defense runs — confirmed always zero, not implemented.** The workbook's
  `Def Runs` term (`IP * (XLOOKUP(Def_rating, ...) + positional_adj)`) reads
  a pitcher's own fielding rating, but `'Projection Constants'!V7:V23` (the
  SP curve) is **literally 0 at every rating step** and `V4` (the positional
  adjustment) is also 0 — verified directly against the workbook, not
  inferred. There's no pitcher fielding rating in the OOTP export either
  (0024 already excluded fielding ratings from `players_pitching`). Per
  explicit decision, `players_pitching_run_value` has no `defense_runs`
  column at all — the term is genuinely inert in the source spreadsheet
  itself, not just unavailable to us.
- **`total_runs`** — `pitching_runs + baserunning_runs + replacement_runs`
  (defense runs omitted as above; same as summing the workbook's
  `SUM(DB3:DE3)` once the always-zero Def Runs term is dropped).
- **Runs/Win — dynamic, not a fixed constant.** Unlike `BatterProjection`'s
  fixed `RUNS_WIN = 9.92`, the pitcher formula blends league-average RA/9
  and the pitcher's own projected RA/9, weighted by how much of an 18-IP
  "full game" their average outing (`IP / GS-or-G`) covers:
  `((((18 - IP/outing) * RA9_baseline + IP/outing * RA9) / 18) + 2) * 1.5`
  (`'Starting Pitchers'!CE3` / `'Relief Pitchers'!DH3`; the `18`/`2`/`1.5`
  literals aren't named cells in the workbook either — same formula, same
  literals, for both SP and RP). `PitcherProjection` computes this as a
  local in `calc_player_values()` (not stored — like `RUNS_WIN`, it's an
  intermediate, and unlike `RUNS_WIN` it varies per row so storing it
  wouldn't obviously belong on the output table either way).
- **`WAR`** — `total_runs / runs_per_win`. **Reliever leverage adjustment
  deliberately omitted.** The workbook multiplies RP (only) WAR by an
  `XLOOKUP` against a Leverage rating (High=1.5/Medium=1.0/Low=0.75,
  `'Weighting Constants'!$A$18:$B$20`) — but that Leverage value, like
  Playing Time (§3.4), is a hardcoded manual literal in the template
  (`='Medium'`), not a formula reading real data, and has no source
  anywhere in the OOTP export. Explicit decision: omit the multiplier
  entirely rather than default it to a no-op 1.0x — SP and RP `WAR` use the
  identical `total_runs / runs_per_win` formula in `PitcherProjection`.

**Not covered by this section** (out of scope for 0028, same as batting):
two-way player WAR netting — `players_run_value` and
`players_pitching_run_value` stay fully independent per-table, no combined
figure. See [0028](../tickets/0028-pitcher-run-value-war.md#2-design-choices).

## 3.8 Fastball/Breaking/Offspeed grade percentiles (0034)

**Unlike §3.7, this is not a run-value figure at all** — it's computed the
same way as `stuff_percentile` / `control_percentile` / etc. (a rating
percentile, not runs/WAR), just over a category-level grade instead of one
of the four `players_pitching` aggregate ratings; it's displayed in
`PitcherPercentiles.vue`'s Value section rather than alongside those other
rating percentiles (an explicit UI-grouping call — see below). Not stored
anywhere — computed
live in `get_player_expected_pitching_percentiles.sql` directly from
`players_pitch_repertoire`, using data that didn't exist until
[0029](../tickets/0029-pitcher-pitch-repertoire.md)'s `players_pitch_repertoire`
table landed. Deliberately **not** tied to `players_pitching_run_value` in
any way (an earlier version of this ticket approximated it as a
proportional share of `pitching_runs`; that approach was dropped in favor
of this simpler, more honest one).

- **Category mapping.** Fastball = `fastball`, `sinker`, `cutter`; Breaking
  = `slider`, `curveball`, `knucklecurve`; Offspeed = `changeup`,
  `splitter`, `forkball`, `circlechange`, `knuckleball`, `screwball`
  (`screwball` is the one ambiguous case — grouped under Offspeed as a
  changeup-family pitch; see [0034](../tickets/0034-pitch-type-run-value-percentiles.md)'s
  Design choices).
- **Formula.** For each category, `avg_grade` = `AVG(grade)` over that
  category's pitch types in `players_pitch_repertoire` for a given
  `rating_id` (`pitch_category_filtered`/`target_cat` CTEs) — NULL if the
  pitcher throws nothing in that category. That average is then percentiled
  against the same cohort every other pitching percentile in this query
  uses (same league/date/age-filtered population), higher-is-better, same
  `COUNT(*) / population` mechanism as `stuff_percentile`. A pitcher with no
  pitches in a category simply has no percentile for it (NULL, excluded
  from the comparison population and not returned as a misleading 0) —
  different from how the earlier run-value-based approach handled the
  same case (that one deliberately used `0.0`, since a runs figure can
  meaningfully be zero; a rating percentile of nothing can't).
- **UI labeling and placement.** Displayed as "Fastball/Breaking/Offspeed
  Run Value" in `PitcherPercentiles.vue`'s **Value** section, alongside
  `pitching_runs_percentile` — matching Baseball Savant's "Pitch Type Run
  Value" widget both in naming and layout (explicit product call), even
  though the calculation itself has nothing to do with `pitching_runs` or
  any other runs/WAR figure. The naming choice is consistent with how
  `K %`/`BB %`/`Barrel %`/`Hard-Hit %` elsewhere in the same component
  already borrow Savant's outcome-stat names for OOTP scouting-grade
  percentiles that aren't actually derived from pitch-tracking outcomes
  either.

## 4. Where this is surfaced today

Both `players_pitching_expected` (0026) and `players_pitching_run_value`
(0028) are populated per short heap and, as of
[0027](../tickets/0027-pitcher-api-frontend-wiring.md), surfaced in the UI —
see [Features.md → Player Profile](Features.md#player-profile--playersid)
for the `PitcherPercentiles` component and
[Features.md → Underlying data](Features.md#underlying-data-projections--run-value)
for how the pipeline feeds it.
