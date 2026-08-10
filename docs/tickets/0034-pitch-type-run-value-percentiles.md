# 0034 — Per-pitch-category run-value percentiles: Fastball / Breaking / Offspeed

- **Tag:** feat
- **Status:** Closed
- **Depends on:** [0029](0029-pitcher-pitch-repertoire.md)
- **Blocks:** —

## 1. Problem

`PitcherPercentiles.vue`'s Value section currently shows a single aggregate
"Pitching" run-value percentile bar
(`frontend/src/components/percentiles/PitcherPercentiles.vue:38-44`), with a
comment explicitly flagging the gap this ticket closes:

> Savant's "Pitch Type Run Value" widget breaks this down into
> Pitching / Fastball / Breaking / Off Speed. We only have the aggregate
> today -- per-pitch-type run value is blocked on
> docs/tickets/0029-pitcher-pitch-repertoire.md's pitch-level data existing
> at all.

That data now exists (`players_pitch_repertoire`, populated per-pitch grade
per pitcher, landed via [0029](0029-pitcher-pitch-repertoire.md)'s
[0031](0031-pitch-repertoire-schema.md)/[0032](0032-pitch-repertoire-migration.md)/[0033](0033-pitch-repertoire-report.md)).
This ticket is the follow-up 0029's own Problem section anticipated
("Long-term refinement of the pitcher projection system... exploratory
future work") — three new percentiles, **Fastball Run Value**, **Breaking
Run Value**, and **Offspeed Run Value**, each representing the combined
quality of all pitch types a pitcher throws within that category.

## 2. Design choices

- **Pitch-type → category mapping.** The 12 pitch types
  (`fastball`, `slider`, `curveball`, `screwball`, `forkball`, `changeup`,
  `sinker`, `splitter`, `knuckleball`, `cutter`, `circlechange`,
  `knucklecurve` — spelled per `players_pitch_repertoire.pitch_type`, see
  [0031](0031-pitch-repertoire-schema.md)) need bucketing into Savant's
  three categories. Following Savant's own real-world classification:
  **Fastball** = `fastball`, `sinker`, `cutter`; **Breaking** = `slider`,
  `curveball`, `knucklecurve`; **Offspeed** = `changeup`, `splitter`,
  `forkball`, `circlechange`, `knuckleball`, `screwball`. `screwball` is the
  one genuinely ambiguous case (Savant rarely sees it thrown in modern MLB
  and doesn't have a settled bucket for it) — grouped under Offspeed here
  since it's a changeup-family pitch mechanically, but this is a judgment
  call worth revisiting if it reads oddly in practice.
- **Superseded — option (b) (proportional share of `pitching_runs`) was
  implemented, then explicitly rejected by the user**: "this should not be
  tied to the pitcher run value... a percentile of the various grades of
  the current pitch types... an overall pitch category rating should be
  generated then the percentile ranking compared to the rest of pitchers."
  That's option (a) from the original discussion — a rating percentile, not
  a runs figure — chosen instead. Everything below reflects the current
  (a)-based implementation; the (b) writeup above is left in place as a
  record of what was tried and why it was replaced, not as live design.
- **Chosen: (a), rating percentile of average category grade.** For a
  pitcher's `rating_id`:
  ```
  avg_grade(category) = AVG(grade) FROM players_pitch_repertoire
                         WHERE pitch_type IN <category's pitch types>
                         -- NULL if the pitcher throws none in that category
  ```
  percentiled directly against the same league/date/age-filtered cohort
  every other pitching percentile in `get_player_expected_pitching_percentiles.sql`
  already uses — mechanically identical to `stuff_percentile` etc., just
  over a category-aggregated grade instead of one of the four
  `players_pitching` columns. **Not tied to `pitching_runs` or
  `players_pitching_run_value` in any way.** A pitcher with no pitches in a
  category gets `NULL` (excluded from the percentile, not a misleading
  `0`) — different from the rejected (b) approach, where `0.0` runs was
  defensible; a rating percentile of a nonexistent rating isn't.
- **Storage: none — computed live at query time.** No schema changes, no
  projection-step involvement (`PitcherProjection`/`projection.py`
  untouched by this ticket). Two new CTEs in
  `get_player_expected_pitching_percentiles.sql`
  (`pitch_category_filtered` for the comparison population,
  `target_cat` for the target player's own grades, `LEFT JOIN`ed in case a
  pitcher has zero repertoire rows) do the `AVG(...)` aggregation directly
  off `players_pitch_repertoire` per request — matches how every other
  `*_filtered` CTE in that file already works, and repertoire data is small
  enough that this isn't a meaningful cost concern.
- **UI label / section placement.** Displayed as "Fastball/Breaking/
  Offspeed Run Value" (Savant's own widget name) in the **Value** section
  of `PitcherPercentiles.vue`, alongside `pitching_runs_percentile` —
  explicit user call, superseding an earlier version of this ticket that
  placed them in the Pitching (ratings) section on the reasoning that
  they're mechanically a rating percentile, not a runs figure. That
  reasoning is still true and documented in code comments (see
  `valueOrder`'s comment in `PitcherPercentiles.vue`) — the layout groups
  them with Savant's "Pitch Type Run Value" widget regardless, since that's
  the UI grouping being matched, not the calculation.

## 3. Approach

- `backend/app/db/sql_scripts/api/get_player_expected_pitching_percentiles.sql`:
  add `pitch_category_filtered` (cohort-scoped, `GROUP BY rating_id`,
  `AVG(CASE WHEN pitch_type IN (...) THEN grade END)` per category) and
  `target_cat` (same aggregation, unfiltered, scoped to `%(rating_id)s`)
  CTEs; three new `ROUND(...)` percentile blocks
  (`fastball_grade_percentile`, `breaking_grade_percentile`,
  `offspeed_grade_percentile`) using the same `COUNT(*) / population`
  mechanism as `stuff_percentile`; `LEFT JOIN target_cat` onto the final
  `FROM` so a pitcher with no repertoire rows still gets every other
  percentile (not zero rows entirely).
- `frontend/src/components/percentiles/PitcherPercentiles.vue`: three new
  `statLabelMap` entries (same display labels as before); added to
  `valueOrder` alongside `pitching_runs_percentile` (see Design choices
  above); comments updated to describe the rating-percentile mechanism
  instead of the rejected run-value split, and to explain the Value-section
  placement despite that mechanism.
- `docs/wiki/Projections.md` §3.8: rewritten to document the CTE-based
  formula, the NULL-vs-`0.0` distinction from the rejected approach, and
  the label/section-placement reasoning.
- No changes needed to `schema.sql`, `get_pitcher_projection_inputs.sql`,
  `pitcher.py`, or `projection.py` — the rejected (b) approach's edits to
  all four were reverted (`git checkout --` for the latter three, a manual
  edit for `schema.sql` since it also carries 0031's unrelated
  `players_pitch_repertoire` table).
- **Follow-up visual-match work** (user-provided Savant reference
  screenshot, applied to the whole `PitcherPercentiles` component, not just
  the three new stats): `get_player_expected_pitching_percentiles.sql`
  gained one `<stat>_value` raw-value column per displayed percentile
  (`pitching_runs_value`, `fastball_grade_value`, `breaking_grade_value`,
  `offspeed_grade_value`, `era_value`, `xba_value`, `xwoba_value`,
  `stuff_value`, `control_value`, `pbabip_value`, `hra_value`,
  `velocity_value`), read straight off `target_val`/`target_cat`/
  `target_exp`/`target_rate`, no new joins. `PercentileBar.vue` gained an
  optional `value` prop (raw stat shown right of the bar) and a short
  dotted teal underline beneath the label (Savant's leader-line look).
  `PitcherPercentiles.vue` gained a `getStatValue()` formatter (rate stats
  drop the leading `0` per this project's existing `PlayerDetails.vue`
  convention; ERA/velocity/pitching-runs use fixed decimals; everything
  else rounds to an integer grade) and a POOR/AVERAGE/GREAT axis header
  above each section, and the single group-divider from the previous
  iteration of this ticket was removed (superseded by the per-row dotted
  leader + axis header).

**Files involved:**
- `backend/app/db/sql_scripts/api/get_player_expected_pitching_percentiles.sql` (modified)
- `frontend/src/components/percentiles/PitcherPercentiles.vue` (modified)
- `frontend/src/components/percentiles/PercentileBar.vue` (modified)
- `docs/wiki/Projections.md` (modified)

**Verified:** full pytest suite (same 11 pre-existing, unrelated
`test_players.py` failures, no new failures). SQL verified against a
throwaway `mariadbd` instance (same approach as 0031-0033) with **three**
pitchers seeded with different repertoires specifically to exercise the
missing-category case: one with pitches in all three categories, one
missing offspeed entirely, one missing breaking entirely. Hand-verified the
percentile math against all three (e.g. fastball grades 55/50/70 across the
population → the 70-grade pitcher lands at the 67th percentile). This
caught a real bug: the first version returned a misleading `0` (not `NULL`)
for a pitcher's missing category — `COUNT(*)` against a `WHERE x < NULL`
clause returns a real `0`, it doesn't propagate `NULL` outward the way a
plain scalar comparison would — fixed by wrapping each of the three new
percentile expressions in `CASE WHEN target_cat.<category>_grade IS NOT
NULL THEN ... END`. Re-verified after the fix: the missing-category cases
now correctly return `NULL` (confirmed both directly via the query and over
HTTP through the real Flask route, where it serializes as JSON `null`).
Instance torn down after.

The `<stat>_value` raw-value columns added for the visual-match follow-up
were separately verified the same way (throwaway `mariadbd`, real
`get_player_expected_pitching_percentiles.sql`, real Flask route): all 12
values (later trimmed to 4, see below) came back correctly matching the
seeded raw data (e.g. `fastball_grade_value` "55.0000" for a pitcher with
fastball/sinker grades of 60/50, `era_value` 3.7, `xba_value` 0.214),
including DECIMAL columns serializing as numeric strings over JSON the same
way the existing percentile columns already do (`getStatValue()`'s
`Number(raw)` handles that correctly).

**Scoped down further:** raw values are now shown only for genuine
projected statistics (`pitching_runs`, `era`, `xba`, `xwoba`) — not for raw
game ratings/grades (`stuff`, `control`, `pbabip`, `hra`, `velocity`, and
the three pitch-category grades), since several of those borrow outcome-stat
names (`K %`, `BB %`, ...) and showing their raw 20-80 grade next to that
name would misrepresent it as a real rate stat. `get_player_expected_pitching_percentiles.sql`'s
raw-value block was trimmed to the 4 that are actually used;
`PitcherPercentiles.vue`'s `getStatValue()` gained a `PROJECTED_STAT_KEYS`
allowlist. Re-verified the trimmed SQL the same way (throwaway `mariadbd` +
real route) — caught and fixed a real bug in the process: my own SQL
comment for this block contained literal `%` characters (`K %, BB %, ...`),
which broke pymysql's printf-style `%(name)s` parameter substitution
(`query % args` treats any bare `%` as a format directive) — this would
have 500'd the real endpoint, not just my test script, since
`app/api/projections.py` executes this file's SQL the identical
`cursor.execute(sql, {"rating_id": ...})` way. Fixed by rewording the
comment to avoid literal `%` characters entirely.

Frontend (`PitcherPercentiles.vue`, `PercentileBar.vue`) not verified in a
browser — no `node`/`npm` in this sandbox (same caveat as 0033). Reviewed
by inspection:
new `statLabelMap`/`valueOrder` entries follow the exact same shape as
`pitching_runs_percentile`, and a `null` percentile value already fails
`isValidPercentile`'s `0 <= num <= 100` check the same way every other
missing rating does today, so a missing category should just omit that bar
rather than render incorrectly. Worth a manual check once deployed
(remember the backend container needs a restart to pick up `.sql` file
changes too, per the `flask run`-reloader issue this session hit with
0033).
