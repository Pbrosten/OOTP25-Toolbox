# 0048 — Replace "Total" with a season count in the batting career stats table

- **Tag:** fix
- **Status:** Closed
- **Depends on:** —
- **Blocks:** —

## 1. Problem

`PlayerDetails.vue`'s pitching career-stats table already replaced its
totals-row label with a season count: `pitchingTotals` (lines 176-207)
computes `seasons: new Set(pitchingStats.value.map((s) => s.year)).size`, and
the template renders `{{ pitchingTotals.seasons }} Seasons` (lines 358, 368)
instead of a bare "Total". The batting career-stats table — otherwise a
parallel sibling table for position players — never got the same treatment:
its `totals` computed (lines 109-141) has no seasons count, and its three
totals rows (lines 285, 292, 302, one per responsive breakpoint) still
hardcode the literal text `"Total"`. Position players' totals row is less
informative than pitchers' as a result.

## 2. Design choices

- **Mirror pitching's already-established pattern exactly**, rather than
  designing a new label — same `Set`-of-years count, same `"N Seasons"`
  wording.
- **MLB scoping is already handled upstream, no special-casing needed here.**
  The batting table already conditionally fetches MLB-only vs. MiLB-only
  rows (`get_player_career_batting_mlb.sql` / `_milb.sql`, chosen in
  `app/api/players.py:131-160` based on `playerDetails.league_id`), and the
  table header already reflects which one via `({{ playerDetails.league_id
  === 203 ? 'MLB' : 'MiLB' }})` (`PlayerDetails.vue:246`). A season count
  over whatever rows were fetched therefore reads as "seasons in the league
  shown in the header" automatically — exactly how pitching's version
  already behaves, so no additional MLB-filtering logic is needed in the
  count itself.

## 3. Approach

- Add `seasons: new Set(battingStats.value.map((s) => s.year)).size` to the
  `totals` computed (`PlayerDetails.vue:109-141`), alongside the existing
  `totalPA`/`totalAB`/etc. fields.
- Replace the three `<td class="px-2 py-1" colspan="...">Total</td>` cells
  (lines 285, 292, 302) with `{{ totals.seasons }} Seasons`, matching the
  pitching table's markup at lines 358/368.
- **Verified against real data**: `GET /api/players/15/career/batting`
  (Trea Turner, on the dev database populated by ticket 0046's full
  update-db run) returns 16 rows but only 15 distinct `year` values — a
  mid-season stint split produces two rows for the same year. Confirms the
  `Set`-based count is doing real work (not just row-counting) and matches
  pitching's already-proven approach for the same shape of data. Vite HMR
  picked up the change with no compile errors; `vue-tsc -b` (run inside the
  frontend container) shows the same pre-existing unrelated errors in other
  files both before and after this change, none in `PlayerDetails.vue`. No
  browser available in this session to visually confirm the rendered label.

**Files involved:**
- `frontend/src/components/PlayerDetails.vue` (modified)
