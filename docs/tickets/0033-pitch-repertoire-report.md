# 0033 — Pitch repertoire API route + report component

- **Tag:** feat
- **Status:** Closed
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

**Verified:** full pytest suite (same 11 pre-existing, unrelated
`test_players.py` failures, no new failures). `openai.yaml` parses as valid
YAML. Backend routes verified live: spun up another throwaway `mariadbd`
instance (same approach as 0032), loaded `schema.sql`, seeded one pitcher
with 3 repertoire rows, ran the real Flask dev server against it, and
curled all three cases — `GET /api/players/ratings/pitch_repertoire`
(all rows), `GET /api/players/ratings/100/pitch_repertoire` (that
pitcher's 3 rows), and `GET /api/players/ratings/999/pitch_repertoire`
(no rows → `[]`, not a 404, confirming the documented shape) — plus the
frontend's dependency chain, `GET /api/players/1/ratings?latest=true` →
`rating_id`. All correct. Instance torn down after.

No `node`/`npm` available in this sandboxed environment, so the frontend
change (`PitchRepertoire.vue`, `PlayerProfile.vue`) could not be
type-checked (`vue-tsc`) or built/run in a browser — verified by careful
inspection against the sibling components' patterns
(`PitcherPercentiles.vue`'s fetch-latest-rating-then-fetch-data flow,
`PlayerDetails.vue`'s plain-table styling) instead. Flagging this
explicitly since it's the one piece of this ticket not exercised
end-to-end — worth a manual check in a real browser before considering the
UI side fully done.

**Files involved:**
- `backend/app/api/ratings.py` (modified)
- `backend/docs/openai.yaml` (modified)
- `frontend/src/components/PitchRepertoire.vue` (new)
- `frontend/src/views/PlayerProfile.vue` (modified)
- `docs/wiki/Features.md` (modified)
