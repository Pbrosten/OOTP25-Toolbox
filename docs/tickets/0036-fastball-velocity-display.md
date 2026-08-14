# 0036 — Fastball velocity display on pitcher player pages

- **Tag:** feat
- **Status:** Closed
- **Depends on:** —
- **Blocks:** —

## 1. Problem

`players_pitching.velocity` (`schema.sql:244`) is ingested for every pitcher
rating snapshot but never surfaced anywhere in the frontend — grepping for
`velocity` outside `schema.sql` only turns up its use as one of several inputs
to `get_player_expected_pitching_percentiles.sql`'s percentile math
(`api/get_player_expected_pitching_percentiles.sql:293-298`), never as a
standalone display value. The column isn't a raw MPH reading either — it's a
1-20 OOTP scale index, each step mapping to a MPH band (20 = "100+ MPH" down
to 1 = "75-80 MPH", user-supplied mapping) — so there's no query that could
show a plain "MPH" number even if one existed. `PitcherPercentiles.vue`
already renders a "Fastball Velo" percentile bar (`velocity_percentile`,
`statLabelMap` at `PitcherPercentiles.vue:38`) but with no value next to it —
`PercentileBar.vue` has a raw-value slot (`value` prop, shown right of the
bar, Savant-style) that every genuinely-projected stat uses (xERA, xBA, ...)
but `velocity_percentile` doesn't, since the backend never selected the raw
rating alongside it.

**Revision note:** an earlier version of this ticket placed the value in
`PlayerDetails.vue`'s bio line instead (`/details` route, gated on
`position === 'P'`). Implemented and verified working end-to-end, but the
user clarified after seeing it live that it belongs next to the existing
"Fastball Velo" percentile bar under Pitching in `PitcherPercentiles.vue`,
not in the player-info bio line. That version was reverted; this revision
reflects the corrected placement.

## 2. Design choices

- **Where the value comes from.** `get_player_expected_pitching_percentiles.sql`
  already joins `players_pitching AS target_rate` for the target player
  (`target_rate` at line 315) and already uses `target_rate.velocity` to
  compute `velocity_percentile`. **Chosen:** add `target_rate.velocity AS
  velocity_value` to the existing raw-value SELECT block (alongside
  `pitching_runs_value`/`era_value`/`xba_value`/`xwoba_value`) rather than a
  new route or a new query — it's the same row already being read, just not
  selected.
- **Raw-value exception to the existing PROJECTED_STAT_KEYS rule.**
  `PitcherPercentiles.vue`'s `getStatValue()` deliberately withholds a raw
  value for ratings-based percentiles (`stuff`/`control`/`pbabip`/`hra`)
  because their Savant-borrowed labels ("K %", "Hard-Hit %", ...) would
  misrepresent a 20-80 grade as a real rate stat if shown as a raw number
  (see the existing comment at `PitcherPercentiles.vue:109-116`).
  **Chosen:** velocity is the one exception — "Fastball Velo" isn't a
  borrowed label, it's literally what the 1-20 rating encodes — so
  `velocity_percentile` gets special-cased in `getStatValue()` ahead of that
  rule, mapping the raw index through a lookup table instead of a numeric
  formatter.
- **Index → MPH-band mapping — where it lives.** The mapping is a fixed
  20-entry lookup table with no source-of-truth column anywhere in OOTP's
  export (it's a UI-only convention baked into the game itself). **Chosen:**
  a plain `VELOCITY_MAP` object literal in `PitcherPercentiles.vue`, next to
  the `getStatValue()`/`statLabelMap` logic it feeds — not a DB table, since
  it's a static display lookup with no query ever needing to join against
  it.

## 3. Approach

- `backend/app/db/sql_scripts/api/get_player_expected_pitching_percentiles.sql`:
  add `target_rate.velocity AS velocity_value` to the raw-value SELECT block
  (after `xwoba_value`).
- `frontend/src/components/percentiles/PitcherPercentiles.vue`: add the
  `VELOCITY_MAP: Record<number, string>` constant; special-case
  `velocity_percentile` at the top of `getStatValue()` to look up
  `VELOCITY_MAP[Number(xStatsPitch.value?.velocity_value)]` instead of going
  through `PROJECTED_STAT_KEYS`. No template change needed —
  `PercentileBar`'s existing `:value="getStatValue(key)"` binding picks it up
  automatically once `getStatValue` returns something for that key.
- Verify against the running dev stack: confirm
  `GET /api/players/ratings/<rating_id>/expected/pitching/percentiles`
  returns `velocity_value`, and that it renders as an MPH band next to the
  "Fastball Velo" bar for a real pitcher.

**Files involved:**
- `backend/app/db/sql_scripts/api/get_player_expected_pitching_percentiles.sql` (modified)
- `frontend/src/components/percentiles/PitcherPercentiles.vue` (modified)

**Verified:** confirmed live against the running dev stack (`podman
compose`) rather than a throwaway DB, since the query change is additive to
an existing, already-populated live query — `curl
localhost:5000/api/players/ratings/1066144/expected/pitching/percentiles?mlb=true`
(a real pitcher, Paul Skenes) now returns `"velocity_value": 18` alongside
`"velocity_percentile": "97"`, and the frontend module served by the running
Vite dev server (`curl localhost:5173/src/components/percentiles/PitcherPercentiles.vue`)
shows the compiled `VELOCITY_MAP` lookup wired into `getStatValue`. Full
pytest suite: same 11 pre-existing, unrelated `test_players.py` failures
(mocked-cursor/MagicMock JSON-serialization issue, not from this change), no
new failures. `npx vue-tsc -b --noEmit` shows only pre-existing `@/`-alias
resolution errors, none referencing `PitcherPercentiles.vue`. Confirmed by
the user in the browser; per their follow-up, `VELOCITY_MAP`'s band strings
were trimmed to drop the trailing "MPH" (e.g. `98-100` instead of
`98-100 MPH`) since it's redundant next to the "Fastball Velo" label.
