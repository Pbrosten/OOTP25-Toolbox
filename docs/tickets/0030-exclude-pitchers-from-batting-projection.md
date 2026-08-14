# 0030 — Exclude pitchers from the batting projection workflow (pending a future TWP tag)

- **Tag:** fix
- **Status:** Open
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

- **Where to filter?** Options: (a) `get_projection_inputs.sql` only — stops
  the wasted projection compute but leaves the ingestion bloat in
  `players_batting`/`players_batting_talent`; (b) `migration_short.sql`'s
  `players_batting`/`players_batting_talent` INSERTs — stops the rows from
  ever landing in `ootp` at all, mirroring
  [0026](0026-pitcher-projection-methodology.md)'s precedent of filtering
  `players_pitching`'s population at the migration layer ("since that's
  where the population question actually lives"). **Recommend (b)**, likely
  still paired with a defensive check at the fetch/projection layer the way
  `PitcherProjection.__init__` defensively re-checks role even though
  `migration_short.sql` already filters it — left for the implementer to
  decide, not resolved here.
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
- **Outstanding:** `ootp.players.position` still has un-normalized raw
  numeric codes (`'1'`-`'9'`) for some rows even after `migration_short.sql`'s
  own `UPDATE players SET position = CASE position WHEN '1' THEN 'P' ...`
  block — confirmed live (`SELECT DISTINCT position FROM players` returns
  both string and numeric values in the same database). A `position != 'P'`
  filter could miss rows still numerically coded `'1'`. Whether that's this
  ticket's problem to fix or belongs to a separate pre-existing
  data-quality ticket isn't decided here.

## 3. Approach

- Add a population filter (`position != 'P'`, or the staging-side numeric
  equivalent — `staging.players_batting` has its own `position` column,
  same shape as `staging.players_pitching.position`/`role` did before 0026)
  to `migration_short.sql`'s `players_batting` and `players_batting_talent`
  INSERT statements, mirroring 0026's `players_pitching` population-filter
  precedent (`WHERE ... AND s.role IN (11, 12, 13)`).
- Decide whether `get_projection_inputs.sql` also needs its own defensive
  filter (dual-layer) or whether excluding at ingestion is sufficient, since
  it already inner-joins `players_batting`.
- No schema changes — this is purely a population filter on existing
  tables, not a new column.
- Verify against a real dump: row-count comparison for `players_batting` /
  `players_batting_expected` before and after, confirming the `position =
  'P'` rows disappear and no non-pitcher rows are accidentally caught by
  whatever numeric/string position check is used (see the Outstanding note
  above).

**Files involved:**
- `backend/app/db/sql_scripts/migration/migration_short.sql` (modified)
- `backend/app/db/sql_scripts/migration/get_projection_inputs.sql` (modified, if dual-layer filter is chosen)
