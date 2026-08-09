# 0033 — Pitch repertoire API route + report component

- **Tag:** feat
- **Status:** Open
- **Depends on:** [0032](0032-pitch-repertoire-migration.md)
- **Blocks:** —

## 1. Problem

With `players_pitch_repertoire` populated (0032), there's still no way to
see it — no API route reads the table, and no frontend surfaces "how many
pitches does this pitcher throw, and how good is each one," the gap
[0029](0029-pitcher-pitch-repertoire.md) was filed to close.

## 2. Design choices

- **Route location: `app/api/ratings.py` vs. `app/api/projections.py`.**
  `ratings.py` holds raw-ratings passthrough routes (`/batting`,
  `/basepath`, `/fielding`, `/positions`, each with a `GET all` +
  `GET /<rating_id>` pair reading straight off one table, no derived/
  percentile math) — `projections.py` holds computed/percentile routes.
  Pitch repertoire is a raw-ratings passthrough (list of rows from one
  table), not a projection. **Chosen:** add to `ratings.py`, following the
  existing `get_X_ratings` / `get_X_rating_by_id` pair pattern exactly
  (note: `players_pitching`/`players_pitching_talent` themselves still have
  no route here either — pre-existing gap, not this ticket's problem to
  fix).
- **Response shape: flat rows vs. grouped-by-pitch-type.** The table is
  `(rating_id, pitch_type, grade, talent_grade)` rows.  A pitcher with 3
  pitches has 3 rows for the same `rating_id`. **Chosen:** return the flat
  row list for `GET /pitch_repertoire` (matches every other route in this
  file, which return raw table rows), and for `GET
  /<rating_id>/pitch_repertoire` return all rows for that pitcher as a
  list (not a single object) — the one place this file's existing "single
  row by id" pattern doesn't quite fit, since `rating_id` isn't unique in
  this table. Document that explicitly in the route's docstring so it's
  not mistaken for the same shape as `get_batting_rating_by_id`.
- **Report component vs. reusing `PitcherPercentiles`.** `PitcherPercentiles`
  (0027) is a percentile-against-population view (bars comparing a pitcher
  to the league). A repertoire breakdown has no comparison population — it's
  just "this pitcher's pitches and grades," closer to a small table/list.
  **Chosen:** new component, rendered alongside (not inside)
  `PitcherPercentiles` on `PlayerProfile.vue` for pitchers.
- **Grade display: raw 20-80 number vs. converted to a letter/bar scale.**
  `PitcherPercentiles`/`BatterPercentiles` use `PercentileBar` (a
  population-relative visual), which doesn't apply here (no population,
  see above). **Chosen:** plain numeric grade display (matches how
  `PlayerDetails`/raw rating views already show 20-80 numbers elsewhere in
  this codebase) — no new visual-scale component; can be revisited later if
  it reads poorly in practice.

## 3. Approach

- `backend/app/api/ratings.py`: add
  ```python
  @bp.route("/pitch_repertoire", methods=["GET"])
  def get_pitch_repertoire():
      ...  # SELECT * FROM players_pitch_repertoire

  @bp.route("/<int:rating_id>/pitch_repertoire", methods=["GET"])
  def get_pitch_repertoire_by_id(rating_id):
      ...  # SELECT * FROM players_pitch_repertoire WHERE rating_id = %s
            # returns a list (possibly empty), not a single object/404
  ```
  following the existing routes' `get_db()`/`try`/`close_db()` pattern.
- `backend/docs/openai.yaml`: document the two new routes and a
  `PitchRepertoireEntry` schema, mirroring the existing `BattingExpected`-
  style entries.
- `frontend/src/components/PitchRepertoire.vue` (new): fetches
  `/api/players/ratings/<rating_id>/pitch_repertoire`, renders a simple
  list/table of `pitch_type` → `grade` (and `talent_grade`), sorted by
  `grade` descending. Empty state for `position !== 'P'` or a pitcher with
  zero rows (shouldn't happen per 0029's inspection, but the endpoint can
  legitimately return `[]`).
- `frontend/src/views/PlayerProfile.vue`: render `PitchRepertoire` alongside
  `PitcherPercentiles` in the `position === 'P'` branch.
- `docs/wiki/Features.md`: document the new report.

**Files involved:**
- `backend/app/api/ratings.py` (modified)
- `backend/docs/openai.yaml` (modified)
- `frontend/src/components/PitchRepertoire.vue` (new)
- `frontend/src/views/PlayerProfile.vue` (modified)
- `docs/wiki/Features.md` (modified)
