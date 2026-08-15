# 0062 — Ingest team level and parent-org data

- **Tag:** feat
- **Status:** Closed
- **Depends on:** —
- **Blocks:** [0063](0063-roster-depth-chart-query-api.md)

## 1. Problem

[0039](0039-roster-optimization-org-depth.md) (Roster Optimization &
Organizational Depth) needs to distinguish an org's MLB roster from its
AAA/AA/A/Rookie affiliates, but `teams` (`schema.sql:41-53`) has no
level/affiliate columns — every team ingested today (MLB and MiLB alike)
looks identical except for `league_id`.

Inspected a real dump export (`TEST.lg` save,
`dump_2024_yearly/mysql/teams.mysql.sql`) to check what's available, same
approach [0053](0053-contract-service-time-schema.md) used for the
contract/service-time gap. Found `teams` already carries exactly what's
needed in the raw OOTP export: `parent_team_id INT` and `level INT`,
neither currently in `DUMP_INCLUSION_LIST`'s ingested columns (staging
mirrors the raw dump as-is, so `staging.teams` already has both columns —
only `ootp.teams` and the migration query need updating).

**Real data findings (TEST.lg save, 259 teams total):**
- `level` cleanly partitions into MLB/MiLB tiers by `league_id`:
  - `1` → league 203 (Major League Baseball), 34 teams
  - `2` → leagues 204/205 (International League, Pacific Coast League —
    AAA), 32 teams
  - `3` → leagues 206/207/208 (Eastern/Southern/Texas League — AA), 36
    teams
  - `4` → leagues 209/210/211/212/213/252 (South Atlantic, Midwest,
    California, Carolina, Northwest, Florida State — A/High-A), 72 teams
  - `6` → leagues 217/218/219/234 (Arizona Complex, Florida Complex, +1
    more, Dominican Rookie — Rookie/Complex), 83 teams
- `level = 5` is **not** a real minor-league tier in this save — it's 2
  "All-Star" exhibition teams (league 215, no real league name, `name =
  'All-Star'`), both with `parent_team_id = 0`. An anomaly of this save's
  setup, not a general OOTP convention — needs excluding wherever level is
  used to build an org's affiliate tree, the same way `team_id = 999` (Free
  Agents) is already excluded in existing queries (e.g.
  `get_player_expected_value_percentiles.sql`).
- Every MiLB team's `parent_team_id` already points **directly** at its
  parent MLB team (confirmed: level-2/3/4/6 rows' `parent_team_id` values
  all fall in the MLB team-id range) — there's no intermediate chain to
  walk. `team_affiliations.mysql.sql` (also present in the raw export,
  flattens each MLB team's full affiliate list) is redundant with
  `parent_team_id` for this purpose and does not need ingesting.
- `teams.mysql.sql`'s existing `SELECT * FROM staging.teams` migration
  already ingests all 259 teams (MLB and MiLB alike, including the 2
  All-Star rows) with no filter — this ticket only adds columns to that
  existing row set, it doesn't change which teams get ingested.

## 2. Design choices

- **Ingest `parent_team_id` and `level` as plain columns, no new lookup
  table.** Mirrors the codebase's existing convention of hardcoding
  small, stable ID meanings inline rather than ingesting a `leagues`
  table for names (e.g. `league_id === 203` means MLB in three frontend
  files today, `PitcherProjection.ROLE_MAP` hardcodes role codes 11/12/13
  — see [0026](0026-pitcher-projection-methodology.md)). **Chosen:** same
  pattern — `level` stays a raw `INT`, with the 1/2/3/4/6→MLB/AAA/AA/A/
  Rookie mapping (and the level-5 exclusion) implemented as a constant
  wherever it's consumed (0063's query layer), not stored as a name.
- **No new table for affiliate relationships.** Confirmed above that
  `parent_team_id` alone (already a column on `teams`) is sufficient —
  `team_affiliations` would only duplicate it. **Chosen:** don't ingest
  `team_affiliations` at all.
- **Outstanding:** none — this is a small, mechanical two-column addition
  to an existing table, no real alternatives considered.

## 3. Approach

- `backend/app/db/sql_scripts/schema.sql`: add `parent_team_id INT` and
  `level INT` to the `teams` table definition.
- `backend/app/db/sql_scripts/migration/migration_long.sql`: add
  `parent_team_id` and `level` to the existing `INSERT INTO teams ...
  SELECT ... FROM staging.teams ON DUPLICATE KEY UPDATE ...` block (both
  the column list and the `ON DUPLICATE KEY UPDATE` clause). No change to
  the synthetic `team_id = 999` Free Agents row — it stays `NULL`/absent
  for both new columns, consistent with it not being a real team.
- `staging.py`'s `DUMP_INCLUSION_LIST` already includes `"teams.mysql"` —
  no change needed there; staging ingestion mirrors the raw dump's full
  column set automatically.
- Verify on a throwaway DB (established pattern for schema/migration
  changes): run `init-db` + a real yearly-heap `update-db` against the
  `TEST.lg` save, confirm `ootp.teams.level`/`parent_team_id` match the
  raw dump's values for a sample of MLB and MiLB teams, and that the
  level-1/2/3/4/6 counts (34/32/36/72/83) and the 2 level-5 rows match
  what was found during investigation above.

**Files involved:**
- `backend/app/db/sql_scripts/schema.sql` (modified)
- `backend/app/db/sql_scripts/migration/migration_long.sql` (modified)

**Verified** on a throwaway MariaDB container (established pattern, no
persistent volume): loaded `schema.sql` into a scratch `ootp` DB and the
real `TEST.lg` `dump_2024_yearly/mysql/teams.mysql.sql` export into a
scratch `staging` DB, then ran the updated `teams` INSERT block from
`migration_long.sql`. Confirmed:
- `staging.teams`: 259 rows, 6 distinct `level` values, matching the
  investigation above.
- `ootp.teams` after migration: 260 rows (259 real + the synthetic
  `team_id = 999` Free Agents row), 6 distinct `level` values, `COUNT
  (parent_team_id) = 259` (i.e. every real team got a value, only the
  synthetic row is `NULL`).
- Level-1 (MLB) teams have `parent_team_id = 0` (e.g. Arizona/Atlanta/
  Baltimore). Level-2/3/4/6 affiliates have `parent_team_id` pointing
  directly at their MLB parent (e.g. team 33 "Columbus", level 2, `parent_
  team_id = 8`). Level-5 rows are the 2 "All-Star" teams, `parent_team_id
  = 0` as expected. `team_id = 999` (Free Agents) correctly has `level`/
  `parent_team_id` both `NULL` — it's never part of the `SELECT FROM
  staging.teams`.
- Backend suite: 118 passed (no Python touched by this ticket).

Did **not** apply to the persistent dev-stack `ootp` database — per user
request, held off for now. 0063/0064 will need this run against the real
dev DB before they can build/verify against live `level`/`parent_team_id`
data; ask before running `update-db` against it.

## Post-implementation correction (found during 0064)

`level = 1` alone turned out **not** to mean "real MLB team" — this save
also tags 4 exhibition teams (AL/NL All-Stars: 31/32, AL/NL Future Stars:
184/185) as `level = 1`. They have no real city (`city_id = 0` in the raw
export, vs. every real franchise's nonzero id) and never roster real
players (`SELECT COUNT(*) FROM players WHERE team_id IN (31,32,184,185)` →
0 for all four, live-verified). `division_id`/`league_id` can't
distinguish them either — real teams (e.g. Atlanta) legitimately share
`division_id = 0` too.

**Fixed:** added `city_id INT` to `teams` (same schema.sql/migration_
long.sql pattern as `parent_team_id`/`level`), the reliable "is this a
real team" signal — `city_id != 0` now gates both the team-listing and
depth-chart-lookup queries added in
[0064](0064-roster-depth-chart-frontend.md). Verified on a throwaway DB
the same way as this ticket's original change: teams 31/32/184/185 get
`city_id = 0`, every real MLB team (spot-checked Arizona, Atlanta) gets
its real nonzero `city_id`.

**Files involved (addendum):**
- `backend/app/db/sql_scripts/schema.sql` (modified again — `city_id`)
- `backend/app/db/sql_scripts/migration/migration_long.sql` (modified
  again — `city_id`)
