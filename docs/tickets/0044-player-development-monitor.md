# 0044 — Player Development Monitor

- **Tag:** feat
- **Status:** Open
- **Depends on:** —
- **Blocks:** —

## 1. Problem

`docs/improvements/expanded-functionality.md`'s Tier 1 #7 wants the app to
detect meaningful changes in player ability/performance over time — tracking
monthly/yearly changes in offensive/pitching/defensive ratings, speed,
stuff/movement/control, actual vs. projected performance, and age-relative
development/decline — surfacing alerts like "contact ability has improved
substantially and production has followed" or "veteran pitcher's stuff and
velocity are declining faster than expected."

This is the one stagged functionality in this document that's buildable
almost entirely from data the app already ingests: `players_rating` is
uniquely keyed on `(player_id, rating_date)`
(`backend/app/db/sql_scripts/schema.sql:177-184`), so every monthly/yearly
heap already produces a new snapshot row per player, and
`players_batting`/`players_pitching`/`players_fielding`/`players_basepath`
all carry the underlying rating values per snapshot. Nothing currently reads
across snapshots to compute a delta or trend, though — every existing
consumer (`PercentileBar.vue`, `BatterPercentiles.vue`,
`PitcherPercentiles.vue`) only ever looks at the latest rating.

Filed as an epic-tracker ticket, standalone (no other stagged functionality
shares this exact scope, though it overlaps with
[0043](0043-prospect-pipeline.md)'s "development trajectory" — see that
ticket's Design choices for the intended reuse direction).

## 2. Design choices

- **Outstanding — what counts as a "meaningful" change.** The source doc's
  examples imply some threshold/significance test (a few points of rating
  drift heap-to-heap is noise; a sustained multi-heap trend or a large
  single-heap jump is signal), but doesn't specify one. This is the central
  open design question — needs its own pass (e.g. rolling-window comparison,
  a minimum-delta threshold, or a z-score against that player's own
  historical variance) before implementation can start, the same way
  [0026](0026-pitcher-projection-methodology.md) needed a resolved
  methodology before its ticket could be scoped.
- **Outstanding — age-relative-development comparison.** "Age-relative
  development" implies comparing a player's trajectory against typical
  aging curves for their age — the same age-curve gap flagged in
  [0026](0026-pitcher-projection-methodology.md)'s Design choices
  (age-development is currently skipped entirely in both projection
  classes). Whether this ticket needs to build that curve itself or can ship
  without the age-relative comparison (raw trend only) for a v1 is not
  decided.
- **Outstanding — actual vs. projected performance tracking.** Ratings
  snapshots exist per heap, but *actual in-game performance* per heap
  doesn't — `players_career_batting_stats`/`players_career_pitching_stats`
  are year-scoped season totals, not per-heap deltas, so comparing "did
  actual production follow the ratings change" needs either deriving a
  season-to-date-at-this-heap-date slice (not currently possible — career
  stats aren't heap-dated) or accepting a coarser year-over-year comparison.
  Not decided; may be a v2 refinement on top of the ratings-trend half,
  which has no such gap.
- **Resolved — no new ingestion needed for the ratings-trend half.** Unlike
  every other epic in this batch, the core "track rating changes over time"
  functionality has zero data gaps — it's a read-only aggregation over
  already-ingested snapshots. This makes it the most self-contained of the
  seven stagged functionalities and a reasonable one to prioritize first if
  sequencing across epics is being considered (see
  [0038](0038-gm-command-center.md)'s Outstanding note on build order).

## 3. Approach (epic outline — needs further breakdown before implementation)

- Resolve the "meaningful change" threshold question first — it's the
  actual product of this ticket, everything else is plumbing.
- Backend: a delta/trend query layer joining consecutive (or windowed)
  `players_rating` snapshots per player across whichever rating tables are
  in scope, likely a new SQL script under `app/db/sql_scripts/api/` plus a
  route (extends `app/api/ratings.py` or a new blueprint).
- Alert generation: once thresholds are resolved, a rule layer that turns
  detected deltas into the source doc's narrative-style alerts.
- Frontend: likely a trend view on the existing player detail page
  (`frontend/src/components/PlayerDetails.vue`) — a small multi-heap
  sparkline/delta per rating category — rather than a standalone page,
  since it's inherently player-scoped.
- Output feeds [0043](0043-prospect-pipeline.md)'s "development trajectory"
  need once built (see that ticket's Design choices).

**Files involved:**
- TBD once broken into sub-tickets — likely a new SQL script under
  `backend/app/db/sql_scripts/api/`, a route in `backend/app/api/ratings.py`
  (or new blueprint), and `frontend/src/components/PlayerDetails.vue`
  (modified).
