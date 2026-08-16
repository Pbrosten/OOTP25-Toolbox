# 0074 — League-wide prospect leaderboard

- **Tag:** feat
- **Status:** In-Progress
- **Depends on:** [0069](0069-prospect-query-layer-api.md), [0072](0072-prospect-risk-adjustment.md)
- **Blocks:** —

## 1. Problem

The Prospect Pipeline (0069/0070) is org-scoped by design — you pick a
team, you see that org's farm system. There's no way to ask "who are the
best prospects in the entire league," ranked against each other rather
than just within one organization — the kind of view a GM needs to
identify trade targets outside their own system or benchmark their own
farm against the league.

`GET /api/prospects` technically supports an unfiltered call (no
`team_id`), but 0069's own verification found that costs ~46 seconds
league-wide (6,395 candidates in the `TEST.lg` save at the time) —
computing `BatterProjection`/`PitcherProjection` twice per candidate plus
a trend query, all at request time, with no caching or persistence. FV 30
exclusion (0072) and the age gate (0043 post-close correction) shrink the
*returned* list, but not the per-candidate computation cost that happens
before either filter applies — a true league-wide leaderboard is still
asking this endpoint to do the expensive part for every prospect-eligible
player in the save, in one request.

## 2. Design choices

Resolved via a direct design conversation with the user:

- **Resolved — persist FV/value per heap into a new table, rather than
  computing at request time.** Reverses 0068's original "no new table,
  point-in-time function" call — that call was made when the endpoint was
  always org-scoped (0069's ~1.6s single-org timing held up fine); a true
  league-wide leaderboard is a different problem. New table follows the
  exact pattern `players_run_value`/`players_pitching_run_value` already
  use for `BatterProjection`/`PitcherProjection` output: one row per
  `rating_id`, computed and persisted during `update-db`'s heap
  processing, read at request time as a plain indexed `SELECT` with zero
  runtime projection calls. Adds real compute cost to heap processing
  (once per heap, not per request) — acceptable tradeoff for a
  request-time cost that was measured at ~46s.
- **Resolved — extend `GET /api/prospects`, not a new URL.** The existing
  org-scoped contract (`team_id` present, live-computed, unchanged) stays
  exactly as-is. Leaderboard mode is a *new query param*
  (`?leaderboard=1`, not just "`team_id` absent") — an unfiltered call
  with no `team_id` today already means "every prospect in the league,
  flat array," and silently repurposing that same shape for a
  structurally different curated response would be a breaking change for
  no reason; an explicit param avoids that ambiguity while still sharing
  one endpoint/route per the user's choice.
- **Resolved — curated sub-leaderboards, not one flat sortable list.**
  Leaderboard mode returns three named sections in one response: Top 100
  overall, top 10 per position, top 10 per level — not a single flat list
  with filters layered on top (that's what the org-scoped mode already
  is, just unfiltered). Ranked by `fv`, `surplus_value` tiebreak.
- **Resolved — real pagination on the "Top 100 overall" section.** Page/
  page_size params (default ~50), since even a fast indexed read
  shouldn't return/render an unbounded list in one response. The
  per-position/per-level sections are fixed-size (top 10 each) and don't
  need their own pagination.
- **Resolved (not asked directly, low-stakes/reversible) — frontend entry
  point.** A new route alongside the existing org picker
  (`ProspectPipelinePicker.vue`), not a mode toggle grafted onto the
  org-scoped view — the response shape (three curated sections) is
  different enough from the org-scoped flat table that it warrants its
  own view component, same reasoning 0070 used for building a dedicated
  view rather than repurposing `TeamDepthChart.vue`.

## 3. Approach (epic outline — broken into sub-tickets)

Mirrors the layering 0043's own epic used (0068 → 0069 → 0070):

```
[x] 0075 Persist prospect FV/value per heap (schema + heap-processing calc)
      |
      v
[ ] 0076 Leaderboard query layer + API (?leaderboard=1 mode, pagination)
      |
      v
[ ] 0077 Leaderboard frontend view

[~] = In-Progress   [ ] = Open   [x] = Closed
```

- [0075](0075-persist-prospect-value-per-heap.md) — new
  `players_prospect_value` table (one row per `rating_id`: `fv`,
  `surplus_value`, `expected_war`, `star_odds`, `current_fv`,
  `risk_tag`), plus a new heap-processing step (parallel to
  `app/db/projection.py`'s existing `process_player`/`process_pitcher`,
  short-heap-only, prospect-eligible players only) that runs 0068's
  talent+current calc and persists the result.
- [0076](0076-leaderboard-query-layer-api.md) — `?leaderboard=1` mode on
  `GET /api/prospects`: reads `players_prospect_value` (joined against
  current `players`/`teams` for prospect-definition filtering, same as
  0069's live-compute path does today) instead of running any projection,
  returns the three curated sections, paginates the overall section.
- [0077](0077-leaderboard-frontend-view.md) — new frontend view/route
  rendering the three sections, linked from `ProspectPipelinePicker.vue`.

**Files involved:**
- See each sub-ticket's own Approach section.
