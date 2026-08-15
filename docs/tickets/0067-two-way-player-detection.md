# 0067 — Two-way player (TWP) detection and dual-sided pitching ingestion

- **Tag:** feat
- **Status:** Open
- **Depends on:** —
- **Blocks:** —

## 1. Problem

The 500 error in [0064](0064-roster-depth-chart-frontend.md)'s org depth
chart (11 orgs, 14 players) traced back to genuine two-way players — real
usage confirmed via `players_career_batting_stats`/`players_career_
pitching_stats` (e.g. Bryce Eldridge: 143 G / 569 PA batting **and** 5 G /
8 IP pitching in 2029). This is exactly the gap
[ticket 0030](0030-exclude-pitchers-from-batting-projection.md) deferred:
*"players with average-or-above skill/potential in both hitting and
pitching should be tagged (e.g. `TWP`) and continue receiving both
batting and pitching projections... unresolved and belongs entirely to
that future ticket."* This is that ticket.

**New evidence changes 0030's original assumption.** 0030 believed there
was "no native hook to lean on" and a TWP tag "would have to be *derived*
from rating thresholds." Investigating the 0064 crash found something
more direct: **OOTP's own per-heap `role` field already toggles between
pitcher (11/12/13) and non-pitcher (0) for a TWP, month to month,
tracking which side of their game is currently emphasized** — not a
fixed designation. Confirmed directly against the raw `TEST.lg` export
(`dump_2029_12/mysql/players_pitching.mysql.sql`): Eldridge's December
row is `(43866, 25, 203, position=9, role=0, ...)` — the raw dump
**does** include a pitching-ratings row for him that month, tagged
`role = 0` (non-pitcher), because his recent usage leaned batting that
month.

`migration_short.sql`'s `players_pitching` INSERT (from
[0026](0026-pitcher-projection-methodology.md)) filters
`WHERE s.role IN (11, 12, 13)` — a deliberate, correctly-reasoned filter
at the time (excluding non-pitchers from a table meant only for
pitchers), but it doesn't anticipate a player whose `role` value
legitimately flips back and forth. **Net effect:** whenever a TWP's role
reads `0` in a given heap, this app silently has no `players_pitching`
row for them that month — no pitching rating, no pitching WAR/value, and
(the immediate trigger) a `NULL` `role_group` wherever code assumes every
`position = 'P'` player resolves to `SP`/`RP`
(`get_org_depth_chart.sql`), which crashed the depth chart via a `None`
dict key hitting Flask's default key-sorting JSON serialization. Their
batting side is mostly unaffected — `players_batting`'s parallel filter
(`role NOT IN (11, 12, 13)`) already keeps their batting ratings flowing
in months where their batting-file role isn't a pitcher role, which
appears to be the common case for them, so `players_run_value`/batting
WAR already exists for these players today. It's specifically the
**pitching side that intermittently disappears**.

## 2. Design choices

- **Detection: reuse already-ingested career stats, not rating
  thresholds.** 0030 assumed detection would need inferring "average or
  above" from `players_batting_talent`/`players_pitching_talent` grades
  — genuinely ambiguous (what counts as "average," which fields). The
  investigation above found a much more direct, already-available signal:
  a player has recent-year rows in **both**
  `players_career_batting_stats` and `players_career_pitching_stats`
  (real, in-game usage on both sides) — no threshold judgment call
  needed, no new ingestion. **Outstanding:** exact recency/volume
  cutoff (any PA/IP in the current year? a minimum, to exclude a pure
  pitcher's token pinch-hit appearance or a position player's mop-up
  inning?) — not decided here, resolve when started.
- **Ingestion fix: stop dropping a TWP's pitching ratings when `role`
  reads 0.** Options: (a) for a *detected* TWP (per whatever rule the
  question above lands on), ingest their `staging.players_pitching` row
  regardless of `role`, alongside the existing `role IN (11, 12, 13)`
  path for everyone else; (b) loosen the filter for everyone (drop the
  `role IN (11,12,13)` condition entirely) — rejected up front, since
  0026's original reasoning (every non-pitcher gets a same-shaped
  placeholder row in the raw export) still holds for the non-TWP
  majority, and ingesting a placeholder row for every position player in
  the league would reintroduce exactly the bloat 0026 filtered out.
  **Leaning (a)**, not decided here.
- **What "role_group" (SP/RP) means for a TWP whose `role` value
  fluctuates.** Once ingestion no longer drops the row, `get_org_
  depth_chart.sql`'s `CASE pp.role WHEN 11 THEN 'SP' ...` still needs a
  sane group for a heap where `role = 0` even after the ingestion fix
  (if that specific heap's row genuinely has `role = 0`, not just
  missing). **Outstanding:** default to their most-recent non-zero role,
  or a dedicated "TWP" group distinct from SP/RP, or fall back to the
  existing "Starter" default ([0059](0059-wire-injury-risk-into-surplus-value.md)'s
  precedent for an unrecognized role) — not decided here.
- **Downstream "never net batting/pitching WAR, exclude two-way
  entirely" precedent.** [0056](0056-surplus-value-calculation.md)'s
  surplus-value calculation and [0063](0063-roster-depth-chart-query-api.md)'s
  depth-chart query both currently treat a player with both batting and
  pitching WAR present as `war = NULL` / excluded outright, rather than
  guessing how to combine them — a deliberate simplification at the
  time, not a bug. Once TWP pitching data stops silently disappearing,
  *more* players will hit this "both present" branch more consistently
  (rather than intermittently, whenever the ingestion gap happened to
  apply). **Outstanding:** whether that existing exclusion is still the
  right call once TWP data is reliable, or whether a real two-way value
  combination becomes worth building — explicitly out of scope for this
  ticket, flagged for whoever picks it up next.

## 3. Approach

Not scoped into concrete implementation steps yet — the Outstanding
questions above (detection rule, ingestion-fix shape, role_group
fallback, downstream WAR-netting) need resolving first, mirroring how
this project's other open-design tickets (e.g.
[0066](0066-recalibrate-run-value-constants-per-save.md)) were filed with
an explicit design-question round deferred to start time rather than
assumed.

**Files involved:** TBD once the Outstanding questions above are
resolved — likely `backend/app/db/sql_scripts/migration/migration_short.sql`
(the ingestion filter), `backend/app/db/sql_scripts/api/get_org_depth_chart.sql`
(role_group fallback, once ingestion no longer produces `NULL`), and
downstream consumers flagged above (`contract_value.py`,
`get_org_depth_chart.sql`'s WAR-netting) once their own scope is decided.
