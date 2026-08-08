# 0029 — Pitcher pitch repertoire: number of pitches and per-pitch quality

- **Tag:** feat
- **Status:** Open
- **Depends on:** [0025](0025-pitcher-migration-ingestion.md)
- **Blocks:** —

## 1. Problem

[0024](0024-pitcher-schema-ratings-tables.md) deliberately excluded the 24
per-pitch-type grade columns in `staging.players_pitching`
(`pitching_ratings_pitches_<type>` / `pitching_ratings_pitches_talent_<type>`,
12 pitch types × current/talent) from `players_pitching`/
`players_pitching_talent`, since neither consumer at the time (the schema
itself, [0026](0026-pitcher-projection-methodology.md)'s production
methodology) reads them — `wiki/Projections.md §3.1` confirms the extracted
spreadsheet methodology only ever looks at the `overall` rating block, not
individual pitch grades.

That's correct for 0026's scope, but pitch repertoire and per-pitch quality
are real signal that matters for actual in-game performance and are
currently unrepresented anywhere in `ootp`. Two concrete needs:

1. An analytics report surfacing a pitcher's repertoire (how many distinct
   pitches, and the grade on each) — new ground, no existing feature covers
   this the way batting/fielding percentiles do for hitters.
2. Long-term refinement of the pitcher projection system.
   `BatterProjection`/`PitcherProjection`'s methodology was extracted from a
   spreadsheet built for **manual** use (`docs/resources/OOTP calculator
   blank.xlsx`), which simplified to `overall`-rating-only inputs for
   spreadsheet usability, not because that's the ceiling of what the OOTP
   ratings export supports. Per-pitch data is a plausible input to a more
   accurate future model (e.g. repertoire diversity affecting BABIP/HR-rate
   beyond what a single aggregate `stuff`/`movement`/`control` grade
   captures) — but that's exploratory future work, not a near-term
   replacement for 0026's spreadsheet-derived methodology.

This ticket is filed as an epic-outline, like [0015](0015-pitcher-projection-epic.md)
was — it forks off the main pitcher-projection line after
[0025](0025-pitcher-migration-ingestion.md) (both need
`staging.players_pitching` loaded) rather than feeding into
[0026](0026-pitcher-projection-methodology.md)/[0028](0028-pitcher-run-value-war.md)/
[0027](0027-pitcher-api-frontend-wiring.md), since neither of its two
consumers (analytics report, future projection refinement) depends on that
line's output. Expect this to get broken into schema/ingestion/presentation
sub-tickets the same way 0015 became 0024–0027, once picked up.

## 2. Design choices

- **Storage shape: wide (mirror the raw export, one column per pitch type)
  vs. normalized (one row per pitch actually thrown).** 0024's tables follow
  this project's existing wide-table convention (`players_fielding_position`'s
  `pos1..pos9`), which fits because every player has *some* grade at every
  position/rating slot in that convention. Pitch repertoire is different in
  kind: a pitcher throws some subset of the 12 available pitch types, not
  all of them, so "number of pitches" is fundamentally a count of *which*
  columns are populated, not a fixed-shape row. **Leaning normalized** —
  `players_pitch_repertoire(rating_id, pitch_type, grade, talent_grade)`,
  one row per pitch the player throws — so "number of pitches" is
  `COUNT(*) GROUP BY rating_id` instead of counting non-NULL cells across 12
  fixed columns, and the table doesn't carry ~60-80%-empty rows for pitchers
  with a typical 3-5 pitch mix. **Not fully decided** — see Outstanding.
- **Outstanding: does OOTP actually leave ungrafted pitch types NULL, or
  does every pitcher get a real (if low) grade on all 12 regardless of
  whether they throw it?** 0024 only inspected *column names* in the sample
  heap, not the value distribution of the 24 per-pitch columns. If every
  pitch type carries a real 20-80 value for every pitcher (grade reflecting
  aptitude, not usage), "number of pitches" isn't directly derivable from
  the ratings export at all, and would need either a threshold-based
  heuristic (e.g. "grade > X counts as a pitch they throw") or a different
  source entirely (a `role`/repertoire field, if one exists, or in-game
  usage stats if OOTP exports those). This needs the same kind of real-dump
  inspection 0024 did before the schema/shape question above can be
  answered for real.
- **Analytics-report consumer vs. projection-refinement consumer are
  independent.** The report just needs the raw per-pitch data surfaced
  (read-and-display); projection refinement is a research question about
  whether/how per-pitch inputs improve on 0026's aggregate-rating model,
  with no defined methodology yet. **Chosen:** this ticket only scopes
  storage + ingestion, shared by both; the report and any projection
  refinement work are separate downstream tickets once this lands, not
  designed here.
- **Not reopening vsL/vsR splits.** 0024 also deferred the 16 `vsr`/`vsl`
  columns; those are a separate, still-unaddressed deferral and out of
  scope here — this ticket is specifically about the 24 per-pitch-type
  grade columns.

## 3. Approach (epic outline — needs further breakdown before implementation)

- Inspect a real dump export's `staging.players_pitching` per-pitch columns
  (value distributions, not just names) to resolve the Outstanding question
  above — same method 0024 used (`TEST.lg` save or similar).
- Schema: add a table for per-pitch grades (shape — wide vs. normalized —
  pending the inspection above), FK'd to `players_rating` like the other
  pitching tables.
- Migration: extend `migration_short.sql` with the corresponding
  `INSERT IGNORE ... WHERE r.rating_date = '{{HEAP_DATE}}'` block(s), same
  pattern as 0025 (already re-enables the `staging.players_pitching` load
  this depends on).
- Presentation: a new analytics view/component (report on repertoire +
  per-pitch quality) — separate from `PitcherPercentiles` (0027), since this
  isn't a percentile-against-population view, it's a repertoire breakdown
  for one player.
- Projection refinement: out of scope for implementation here — flag as a
  future research direction once the data exists, not a committed follow-up
  ticket yet.

**Files involved:**
- `backend/app/db/sql_scripts/schema.sql` (modified)
- `backend/app/db/sql_scripts/migration/migration_short.sql` (modified)
- Frontend: new component (TBD, not `PitcherPercentiles`)
