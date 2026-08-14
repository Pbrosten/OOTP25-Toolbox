# 0037 — Split SP/RP percentile cohorts (stop comparing starters to relievers)

- **Tag:** fix
- **Status:** Closed
- **Depends on:** 0027
- **Blocks:** —

## 1. Problem

`get_player_expected_pitching_percentiles.sql` (0027) percentiles every
pitching rating/value/expected-stat against a single pool of all MLB (or
MiLB) pitchers — `expected_filtered`, `ratings_filtered`, `value_filtered`,
and `pitch_category_filtered` (0034) each filter only on position, team,
league, and MLB-age, never on role. Starters and relievers have
systematically different rating profiles (relievers run hotter stuff/velocity
over fewer innings; starters carry control/movement/stamina to survive a
lineup three times), so pooling them together skews both ends: a starter's
`control_percentile`/`movement`-driven ratings get inflated by comparison
against the whole reliever population (who don't need to hold up for 6+
innings), while `stuff_percentile` and the Fastball/Breaking/Offspeed
run-value percentiles (0034) get compressed relative to what they'd show
against true starter peers, since relievers as a group post better raw stuff
grades than starters do. A starter's percentile page currently reads as "hits
his spots, unremarkable stuff" almost by construction, regardless of how his
stuff actually compares to other starters.

## 2. Design choices

- **Cohort split: SP vs. RP, not three-way by raw role.**
  `players_pitching.role` is a 3-value code (11 = Starting Pitcher, 12 =
  Relief Pitcher, 13 = Closer — confirmed in
  [0026](0026-pitcher-projection-methodology.md)'s Design choices), and
  `PitcherProjection` (`backend/app/player_projection/pitcher.py:49`) already
  established the grouping convention this ticket reuses: `ROLE_MAP = {11:
  'SP', 12: 'RP', 13: 'RP'}`. **Chosen:** same two-bucket split here —
  closers stay pooled with relievers, not split into a third cohort, both
  because that's the existing precedent and because a closer-only cohort at
  most MiLB leagues (and plenty of MLB ones) would be too small to
  percentile meaningfully.
- **Where the split is enforced.** Each filtered CTE
  (`expected_filtered`/`ratings_filtered`/`value_filtered`/
  `pitch_category_filtered`) already scopes its comparison pool to
  `p.position = 'P'`; **chosen:** add a role-bucket match against the target
  player's own bucket, using the same SP/else-RP collapse as `ROLE_MAP`
  (`CASE WHEN role = 11 THEN 'SP' ELSE 'RP' END`) rather than comparing raw
  `role` values directly, so 12 and 13 still pool together. `target_player`
  needs a new join to `players_pitching` to pull the target's own `role`
  (currently only reads `players_rating`); `expected_filtered` and
  `value_filtered` need a new join to `players_pitching` for the comparison
  pool's `role` (they don't currently touch that table); `ratings_filtered`
  already selects `pp.*` so its `role` column is already available, just
  unused in the `WHERE`; `pitch_category_filtered` (`players_pitch_repertoire`)
  needs the same new join.
- **Outstanding:** cohort size after the split isn't measured here — MLB SP
  and RP pools are large enough individually that this shouldn't be an issue
  in practice, but MiLB or small-league cohorts could get thin post-split.
  Deferred: not blocking, and the existing age/position/team filters already
  accept whatever cohort size results without a minimum-count guard.

## 3. Approach

- `backend/app/db/sql_scripts/api/get_player_expected_pitching_percentiles.sql`:
  - `target_player`: add `JOIN players_pitching pp ON pp.rating_id =
    r.rating_id`, select `CASE WHEN pp.role = 11 THEN 'SP' ELSE 'RP' END AS
    role_group`.
  - `expected_filtered`: add `JOIN players_pitching AS pp ON pe.rating_id =
    pp.rating_id`, add `AND (CASE WHEN pp.role = 11 THEN 'SP' ELSE 'RP' END)
    = t.role_group` to the `WHERE` clause.
  - `ratings_filtered`: add the same `role_group` condition to its existing
    `WHERE` clause (no new join needed, `pp.role` already selected via
    `pp.*`).
  - `value_filtered`: add `JOIN players_pitching AS pp ON pv.rating_id =
    pp.rating_id`, add the same `role_group` condition.
  - `pitch_category_filtered`: add `JOIN players_pitching AS pp ON
    pr.rating_id = pp.rating_id`, add the same `role_group` condition.
  - No frontend change — `PitcherPercentiles.vue` just renders whatever
    percentiles the API returns; the comparison pool changes, not the
    response shape.
- Verify against a throwaway DB (or the running dev stack's already-loaded
  data, read-only): confirm a real starter's `stuff_percentile` /
  `fastball_grade_percentile` move (typically down, since they're no longer
  boosted by comparison to relievers) and `control_percentile` moves
  (typically down too, since they're no longer inflated by comparison to
  relievers who don't need it as much) relative to current behavior, and
  that a reliever's percentiles shift in the complementary direction.
  Confirm `role_group` collapses 12/13 correctly by checking a closer's
  cohort matches a non-closer reliever's cohort size.

**Files involved:**
- `backend/app/db/sql_scripts/api/get_player_expected_pitching_percentiles.sql` (modified)

**Verified:** against the running dev stack's live data (`podman exec
mariadb`), not a throwaway DB, since this is a read-only cohort-scoping
change over already-populated tables. Confirmed the SP/RP split is a clean
partition of the old unsplit pool for the latest MLB rating snapshot: 141 SP
+ 334 RP = 475, exactly matching the old unfiltered `position = 'P'` count —
no rows dropped or double-counted. Confirmed role 12 and 13 collapse into
the same RP cohort (`role IN (12,13)` count equals the `role_group = 'RP'`
count). Exercised the real route for a starter (Carlos Rodón, rating_id
1064902) and a reliever (Brusdar Graterol, rating_id 1064908) over HTTP —
both return sensible, non-error percentile sets; the reliever's
`control_percentile`/`hra_percentile`/`era_percentile` sit much higher
against a true reliever cohort than they would have pooled with starters,
consistent with the problem this ticket describes. Full pytest suite: same
11 pre-existing, unrelated `test_players.py` failures, no new failures (this
ticket touches no Python code).
