# 0045 — Remove the MLB percentile toggle; don't render percentiles for non-MLB players

- **Tag:** fix
- **Status:** Open
- **Depends on:** —
- **Blocks:** —

## 1. Problem

Both `BatterPercentiles.vue` and `PitcherPercentiles.vue` render a `Switch`
(`mlbComp`, locked via `mlbLock = leagueId === 203`) that's supposed to let a
non-MLB (MiLB) player's percentiles be compared against either the MLB
population or their current league's. In practice the toggle is inert: both
components fetch with `?mlb=${mlbComp.value}` (e.g.
`BatterPercentiles.vue:197-209`, `PitcherPercentiles.vue:203`), but every
backend percentile route reads a **different** query parameter name —
`request.args.get("milb", "false")` (`backend/app/api/projections.py:73`,
and four more identical reads at lines 157/237/319/355). No caller ever sends
`milb`, so `is_milb` is always `0` and every percentile view — MLB or MiLB
player alike — is silently computed against the **MLB** cohort regardless of
the switch's position.

That means today a MiLB prospect's percentiles are already being compared
against MLB regulars, which is misleading, and the switch gives the false
impression that flipping it changes anything. Rather than fix the param-name
mismatch to make cross-cohort comparison actually work, the direction here is
to stop showing percentiles for non-MLB players at all — a proper cohort
comparison for prospects is deferred to the Prospect Pipeline epic
([0043](0043-prospect-pipeline.md)), which already owns age/level-relative
comparison as part of its scope.

## 2. Design choices

- **Chosen: gate the whole percentiles section on `leagueId === 203`,
  matching the existing `mlbLock` condition** — the check for "is this
  player MLB" already exists in both components, so this reuses it rather
  than inventing a new one.
- **Backend `is_milb`/`milb` param: left in place, not deleted.** It's now
  unreachable from these two components (they'll stop varying the `mlb`
  query param, or drop it entirely), but ripping it out of
  `projections.py`/the `.sql` files isn't needed to fix the frontend problem,
  and the Prospect Pipeline epic is a plausible future consumer of exactly
  this cohort-scoping logic (with the param-name bug fixed) if it ends up
  wanting a real non-MLB comparison later. Leaving it is a smaller diff than
  removing and possibly re-adding it.
- **Outstanding — what renders in place of the percentiles section for a
  non-MLB player.** Options: omit the section entirely (page just has less
  content), or show a placeholder message (e.g. "Percentile comparisons are
  only available for MLB players"). Not decided; doesn't block scoping the
  removal itself.

## 3. Approach

- `BatterPercentiles.vue`: remove the `Switch`/`mlbComp`/`mlbLock` state
  (lines 99-100), the `watch(mlbComp, ...)` (lines 110-112), the `Switch`
  template markup (lines 259-269) and its `Switch` import, and stop
  interpolating `mlb=${mlbComp.value}` into the four fetch URLs (lines
  197-209) — MLB is now the only supported comparison, so the param can be
  dropped or hardcoded. Wrap the percentiles-rendering block in
  `v-if="leagueId === 203"`, with a fallback per the Outstanding note above
  for the `else` case.
- `PitcherPercentiles.vue`: identical treatment — same `Switch`/`mlbComp`/
  `mlbLock` pattern at lines 4, 104-105, 115, 229-238, same single fetch at
  line 203.
- No backend changes required (see Design choices).

**Files involved:**
- `frontend/src/components/percentiles/BatterPercentiles.vue` (modified)
- `frontend/src/components/percentiles/PitcherPercentiles.vue` (modified)
