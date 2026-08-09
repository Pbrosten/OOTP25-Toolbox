# 0029 — Pitcher pitch repertoire: number of pitches and per-pitch quality

- **Tag:** feat
- **Status:** In-Progress
- **Depends on:** [0025](0025-pitcher-migration-ingestion.md)
- **Blocks:** [0031](0031-pitch-repertoire-schema.md), [0032](0032-pitch-repertoire-migration.md), [0033](0033-pitch-repertoire-report.md)

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
line's output.

Broken into per-subsystem tickets the same way 0015 became 0024–0027, once
the Outstanding design question below was resolved:
[0031](0031-pitch-repertoire-schema.md) (schema) →
[0032](0032-pitch-repertoire-migration.md) (migration) →
[0033](0033-pitch-repertoire-report.md) (API + report component).
Projection refinement (need 2 above) remains an unscoped future direction,
not a committed ticket. This ticket now serves as the epic tracker.

## 2. Design choices

- **Storage shape: wide (mirror the raw export, one column per pitch type)
  vs. normalized (one row per pitch actually thrown).** 0024's tables follow
  this project's existing wide-table convention (`players_fielding_position`'s
  `pos1..pos9`), which fits because every player has *some* grade at every
  position/rating slot in that convention. Pitch repertoire is different in
  kind: a pitcher throws some subset of the 12 available pitch types, not
  all of them, so "number of pitches" is fundamentally a count of *which*
  columns are populated, not a fixed-shape row. **Chosen: normalized** —
  `players_pitch_repertoire(rating_id, pitch_type, grade, talent_grade)`,
  one row per pitch the player throws — so "number of pitches" is
  `COUNT(*) GROUP BY rating_id` instead of counting non-NULL cells across 12
  fixed columns, and the table doesn't carry mostly-empty rows for pitchers
  with a typical 2-4 pitch mix. Confirmed by the inspection below.
- **Resolved — value distribution of the 24 per-pitch columns.** Inspected
  `staging.players_pitching`'s raw dump directly (`TEST.lg` save, 2029
  yearly heap, `dump_2029_yearly/mysql/players_pitching.mysql.sql`,
  134,808 rows covering every player in the save's history, not just active
  rosters). Findings:
  - The 24 per-pitch columns are **never NULL** — always a SMALLINT, but the
    overwhelming majority of values are **`0`**, not a real 20-80 grade.
    E.g. across all rows, `pitching_ratings_pitches_fastball` is nonzero in
    ~51% of rows (65,950/134,808 are 0) while
    `pitching_ratings_pitches_knuckleball` is nonzero in <0.1%
    (134,758/134,808 are 0) — the zero rate tracks how rare/common each
    pitch type is, exactly what you'd expect from "0 = doesn't throw this,"
    not filler.
  - Restricting to real pitchers (`role IN (11, 12, 13)`, the same
    SP/RP/Closer scoping `migration_short.sql` already uses for the
    `overall` block — see that file's comment above the `players_pitching`
    insert) gives a clean per-player nonzero-pitch-count distribution:
    mode is 2 pitches, with most pitchers in the 2-4 range and a small tail
    up to 7 (n=63,165: 2→57%, 3→21%, 4→12%, 5→2%, 1 or fewer→0.3%). This is
    a believable real-world repertoire spread, not noise.
  - Non-pitchers (`role = 0`, 71,630 rows) have a real nonzero
    `overall_stuff` value (20-55, generic filler present on every player
    row regardless of position) but 88% have **zero** nonzero per-pitch
    columns — confirming the per-pitch block specifically (unlike
    `overall`) tracks actual pitch usage, not a rating every player gets.
  - **Conclusion:** "grade > 0" is a reliable, already-precedented signal
    for "player throws this pitch" — no separate threshold heuristic or
    external repertoire field is needed. The normalized table should be
    populated by inserting one row per `(rating_id, pitch_type)` where
    `pitching_ratings_pitches_<type> > 0`, mirroring the existing
    `role IN (11, 12, 13)` pitcher-scoping already used for the `overall`
    block.
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

## 3. Approach (epic tracker — implementation happens in the sub-tickets below)

- ~~Inspect a real dump export's `staging.players_pitching` per-pitch
  columns (value distributions, not just names) to resolve the Outstanding
  question above~~ — done, see Design choices above.
- [0031](0031-pitch-repertoire-schema.md) — schema:
  `players_pitch_repertoire(rating_id, pitch_type, grade, talent_grade)`,
  FK'd to `players_rating` like the other pitching tables.
- [0032](0032-pitch-repertoire-migration.md) — migration: extend
  `migration_short.sql` with the corresponding `INSERT IGNORE ... WHERE
  r.rating_date = '{{HEAP_DATE}}'` block(s), same pattern as 0025.
- [0033](0033-pitch-repertoire-report.md) — presentation: a new API route
  (`ratings.py`) + report component, separate from `PitcherPercentiles`
  (0027) since this isn't a percentile-against-population view, it's a
  repertoire breakdown for one player.
- Projection refinement: out of scope for implementation here — flag as a
  future research direction once the data exists, not a committed follow-up
  ticket yet.

**Files involved:**
- See sub-tickets 0031–0033.
