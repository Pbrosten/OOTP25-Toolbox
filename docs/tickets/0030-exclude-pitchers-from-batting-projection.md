# 0030 — Exclude pitchers from the batting projection workflow (pending a future TWP tag)

- **Tag:** fix
- **Status:** Closed
- **Depends on:** —
- **Blocks:** —

## 1. Problem

Nothing in the batting ingestion/projection pipeline filters players by
position, so every player OOTP exports batting ratings for — including pure
pitchers — gets run through `BatterProjection` and stored in
`players_batting_expected`. Verified against the real, in-progress `ootp`
database (not guessed): `position = 'P'` accounts for **428,452 of 843,000**
`players_batting` rows (~51%) — more than any other single position, roughly
double the next-largest group (`C`, 74,664). Those rows flow unfiltered
through `get_projection_inputs.sql` → `project_players()` →
`players_batting_expected`, so roughly half of every short-heap batting
projection pass is spent computing and storing batting stats for players who
don't need them.

The one downstream consumer that reads batting value (`get_player_expected_
value_percentiles.sql`) already filters `p.position != 'P'` from its
comparison pool, so the visible UI impact is limited — but the ingestion and
projection cost (a `multiprocessing.Pool` pass, plus `players_batting` /
`players_batting_talent` / `players_batting_expected` row volume) is real
and roughly doubles what's needed. This isn't a data anomaly — OOTP's export
apparently gives every player nominal batting ratings regardless of
position — it's the ingestion pipeline never filtering on position anywhere
upstream of that one percentile query.

## 2. Design choices

- **Where to filter? Resolved: (b), `migration_short.sql`, no dual-layer
  defensive filter needed.** Filtering at the `players_batting`/
  `players_batting_talent` INSERTs (mirroring
  [0026](0026-pitcher-projection-methodology.md)'s `players_pitching`
  precedent) means pitchers never get a `players_batting` row at all. Unlike
  `PitcherProjection.__init__`'s defensive re-check (which guards against a
  bad *value* reaching a class that processes `players_pitching` rows
  directly), `get_projection_inputs.sql` reaches `players_batting` only via
  an **inner join** (`JOIN players_batting as b ON r.rating_id =
  b.rating_id`) — a player with no `players_batting` row is structurally
  absent from that query's result set already, no separate `WHERE` filter
  needed there. No changes made to `get_projection_inputs.sql`.
- **TWP (two-way player) tag — explicitly out of scope for this ticket,
  deferred to a future ticket.** The stated end state: players with
  average-or-above skill/potential in *both* hitting and pitching should be
  tagged (e.g. `TWP`) and continue receiving both batting and pitching
  projections, rather than being excluded outright. Verified there's no
  native hook to lean on: `SELECT DISTINCT position FROM players` on the
  real save returns only single-position codes (`P`, `C`, `1B`, ... plus
  some un-normalized numeric leftovers, see Outstanding below) — no `TWP` or
  equivalent. A real two-way tag would have to be *derived* from rating
  thresholds across both `players_batting`/`players_pitching`'s
  overall/potential columns, not sourced directly from the OOTP export.
  Defining "average or above" and which specific rating fields count is
  unresolved and belongs entirely to that future ticket.
- **This ticket's scope: a blanket position-based exclusion, no TWP
  carve-out.** Every `position = 'P'` player is excluded from the batting
  pipeline, full stop, until a TWP-detection ticket exists and ships. This
  will temporarily under-serve genuine two-way players in saves that have
  them — an explicit, accepted regression until the follow-up lands, not an
  oversight.
- **Resolved — the numeric-position-code Outstanding question, by not using
  `position` at all.** Rather than filter on `ootp.players.position`/
  `staging.players_batting.position` (which needs the numeric→letter `CASE`
  mapping and is exactly the column with the confirmed normalization-timing
  gap — a player inserted earlier in the same run hasn't had that `UPDATE`
  applied yet when `players_batting` is populated), the filter uses
  `staging.players_batting.role` instead — same roster-role code
  `staging.players_pitching.role` already uses (11/12/13 = SP/RP/Closer, 0 =
  non-pitcher), confirmed by 0026 and re-confirmed here directly against a
  real dump export: cross-tabulating `(position, role)` on
  `staging.players_batting` (`dump_2029_yearly`, 134,808 rows), `position=1`
  (Pitcher) pairs with `role IN (11,12,13)` in 63,160 of 63,163 such rows —
  the tiny remainder (13 rows total across all position/role combinations)
  is pre-existing save noise unrelated to this filter, not a Pitcher/role
  mismatch. `role` sidesteps the numeric/letter question entirely — no
  normalization step is involved in either the filter or its input.

## 3. Approach

- Added `AND s.role NOT IN (11, 12, 13)` to `migration_short.sql`'s
  `players_batting` and `players_batting_talent` INSERT statements' `WHERE`
  clauses, mirroring 0026's `players_pitching` precedent. No changes to
  `get_projection_inputs.sql` (see Design choices) and no schema changes.
- **Verified against real data** (the same `TEST.lg` `dump_2029_yearly`
  staging load already sitting in the dev database post-
  [0046](0046-prune-inactive-players.md)): re-ran the position/role
  cross-tab above directly against `staging.players_batting`, and separately
  computed the real per-heap impact by joining to `staging.players` `WHERE
  retired = 0` (matching `players_rating`'s own population filter) — of
  11,706 non-retired players, 5,730 (49%) are pitchers that the new filter
  excludes and 5,976 remain, matching the Problem section's ~51% estimate.
  Did not re-run the full `update-db` pipeline end-to-end for this ticket
  (that only re-validates plumbing already proven working by
  [0046](0046-prune-inactive-players.md)'s full 66-heap run) — the change
  itself is a single added `WHERE` predicate, validated directly against
  real-shaped data rather than through a ~45-minute full pipeline run.
- Not run against the live `ootp` database. `players_batting`/
  `players_batting_talent`/`players_batting_expected` rows already inserted
  by past heap runs (before this fix) aren't retroactively removed — the
  filter only affects new inserts going forward. Existing pitcher rows for
  past heap dates are inert storage, not an ongoing compute cost (`get_
  projection_inputs.sql` and the projection pass are both scoped to the
  *current* heap date each run), so no backfill/cleanup was done here;
  flag if that's wanted as a separate, explicit ask.

**Files involved:**
- `backend/app/db/sql_scripts/migration/migration_short.sql` (modified)
