# 0045 — Remove the MLB percentile toggle; don't render percentiles for non-MLB players

- **Tag:** fix
- **Status:** Closed
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
- **Resolved (user decision) — placeholder message, not silent omission.**
  Asked directly rather than picked unilaterally. Shows "Percentile
  comparisons are only available for MLB players." in place of the stat
  sections for a non-MLB player. The year selector stays regardless (it's
  about which rating snapshot is being viewed, orthogonal to the
  MLB-cohort-comparison question this ticket is about) — but
  `fetchPercentiles()` is skipped entirely for non-MLB players (on mount
  and on year change), not just hidden after fetching, so the misleading
  MLB-cohort comparison call described in the Problem section is never made
  in the first place.

## 3. Approach

- `BatterPercentiles.vue`: removed the `Switch`/`mlbComp`/`mlbLock` state,
  the `watch(mlbComp, ...)`, the `Switch` template markup (and its now-
  orphaned "Current"/"MLB" labels), the `Switch` import, and the `?mlb=...`
  query param on all four fetch URLs — replaced with a plain `const isMlb =
  leagueId === 203`. `fetchPercentiles()` is now only called (on mount and
  on year change) when `isMlb` is true; the four stat-section `v-if`s are
  gated on `isMlb &&` their existing condition, with a `v-if="!isMlb"`
  placeholder paragraph ("Percentile comparisons are only available for MLB
  players.") in the gap. The year `Listbox` is untouched — stays available
  either way.
- `PitcherPercentiles.vue`: identical treatment (same `Switch`/`mlbComp`/
  `mlbLock` pattern, same single fetch, same two stat sections).
- No backend changes (see Design choices).
- **Verified:** Vite HMR picked up both files with no compile errors;
  `vue-tsc -b` (run inside the frontend container) shows the same
  pre-existing baseline errors in both files before and after this change,
  none introduced by it. Cross-checked `isMlb`'s condition against a real
  non-MLB player in the dev database populated by
  [0046](0046-prune-inactive-players.md)'s update-db run:
  `GET /api/players/48372/details` returns `league_id: 234` (Ruben
  Velazquez, a 21-year-old DSL prospect on Cleveland's academy roster) —
  confirms `leagueId !== 203` is a real, reachable case, not just a
  hypothetical. No browser available in this session to visually confirm
  the rendered placeholder.

**Files involved:**
- `frontend/src/components/percentiles/BatterPercentiles.vue` (modified)
- `frontend/src/components/percentiles/PitcherPercentiles.vue` (modified)
