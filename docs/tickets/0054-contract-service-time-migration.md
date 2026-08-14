# 0054 — Ingest contract/salary/service-time: `migration_long.sql`

- **Tag:** feat
- **Status:** Closed
- **Depends on:** [0053](0053-contract-service-time-schema.md)
- **Blocks:** —

## 1. Problem

[0053](0053-contract-service-time-schema.md) adds `players_contract`,
`players_salary_history`, and `players_service_time` to `ootp`'s schema
(and considered, then deliberately dropped, a `players_contract_extension`
table — see 0053's Design choices). Nothing populates the three real tables
yet — `staging.py`'s `DUMP_INCLUSION_LIST` doesn't load the source
`players_contract`/`players_salary_history`/`players_roster_status` dump
files into `staging`, and no migration SQL copies staging → ootp for them.
This is the shared prerequisite [0041](0041-trade-target-finder.md) and
[0042](0042-contract-arbitration-analyzer.md) both need before either can
build contract-dependent scope.

## 2. Design choices

- **Long heap, not short.** Confirmed in 0053: `players_contract`,
  `players_salary_history`, and `players_roster_status` dump files only
  appear in yearly heap directories, never monthly ones. Ingestion belongs
  in `migration_long.sql`, alongside the existing `players`/`teams`
  upserts — not `migration_short.sql`, which only ever adds dated rating
  snapshots.
- **`players_contract_extension` not ingested.** Per 0053's Design
  choices — this pipeline only snapshots contract data once a year, so any
  extension visible in one yearly heap has already been folded into
  `players_contract` (or superseded) by the next one. No `staging.py`
  entry, no migration insert, no schema table.
- **`team_id = 0` remap.** `migration_long.sql`'s existing `players`/
  `players_career_*_stats` inserts already handle staging's `team_id = 0`
  (meaning unrostered/free agent) by remapping to the synthetic `999` "Free
  Agents" team via `CASE WHEN team_id = 0 THEN 999 ELSE team_id END`,
  because `teams` has no `team_id = 0` row to satisfy the FK. Every new
  table here carries a `team_id` FK to `players`, and `players_contract`
  FKs to `players` (not `teams` directly per 0053's schema — no FK on
  `team_id` itself was added there), so this only matters if a `team_id`
  FK to `teams` gets added later. Not needed for the FKs 0053 actually
  created. **Resolved: no remap needed** given 0053's chosen FK shape
  (`player_id` only).
- **`players_salary_history` placeholder rows.** Most players carry a
  `year = 0, salary = 0` row alongside real dated ones (confirmed in 0053's
  sample — e.g. `(1, 0, 0, 0, 33)`). Inserting these would waste a
  `(player_id, year=0)` PK slot with no information. **Chosen:** filter
  `WHERE year != 0` in the migration `SELECT`.
- **`INSERT ... ON DUPLICATE KEY UPDATE` vs `INSERT IGNORE`.** Matches
  0053's "current-state" schema choice — contract/service-time facts change
  year to year (new extension signed, arbitration received, service time
  accrued) and each yearly heap should overwrite the prior snapshot, not
  leave it stale. `players_salary_history` is the one exception: it's
  itself already a historical ledger (one row per `(player_id, year)`, never
  revised after the fact), so `INSERT IGNORE` there matches how
  `players_rating`'s append-only inserts already work elsewhere in this
  pipeline.
- **Note — `players_contract_extension` data quality, for the record.** An
  earlier draft of this ticket ingested `players_contract_extension` before
  0053 reversed that decision. While it was still wired up, a real-dump run
  found 11 of 15884 rows had a genuine non-zero salary schedule — so the
  table isn't universally empty, it's just useless given the yearly-only
  refresh cadence (see 0053). Recorded here in case the cadence assumption
  ever changes.

## 3. Approach

- `staging.py`: add `"players_contract.mysql"` (the `.mysql` suffix keeps
  the prefix match from also sweeping in
  `players_contract_extension.mysql.sql`, which isn't ingested),
  `"players_salary_history"`, `"players_roster_status"` to
  `DUMP_INCLUSION_LIST`.
- `migration_long.sql`: add, after the existing `players` upsert (these all
  FK onto `players`, so must come after it):

  ```sql
  INSERT INTO players_contract (
      player_id, team_id, season_year, years, current_year,
      salary0, salary1, salary2, salary3, salary4,
      salary5, salary6, salary7, salary8, salary9,
      salary10, salary11, salary12, salary13, salary14,
      no_trade, last_year_team_option, last_year_player_option,
      last_year_vesting_option, opt_out
  )
  SELECT
      s.player_id, s.team_id, s.season_year, s.years, s.current_year,
      s.salary0, s.salary1, s.salary2, s.salary3, s.salary4,
      s.salary5, s.salary6, s.salary7, s.salary8, s.salary9,
      s.salary10, s.salary11, s.salary12, s.salary13, s.salary14,
      s.no_trade, s.last_year_team_option, s.last_year_player_option,
      s.last_year_vesting_option, s.opt_out
  FROM staging.players_contract s
  INNER JOIN players p ON s.player_id = p.player_id
  ON DUPLICATE KEY UPDATE
      team_id = VALUES(team_id), season_year = VALUES(season_year),
      years = VALUES(years), current_year = VALUES(current_year),
      salary0 = VALUES(salary0), salary1 = VALUES(salary1),
      salary2 = VALUES(salary2), salary3 = VALUES(salary3),
      salary4 = VALUES(salary4), salary5 = VALUES(salary5),
      salary6 = VALUES(salary6), salary7 = VALUES(salary7),
      salary8 = VALUES(salary8), salary9 = VALUES(salary9),
      salary10 = VALUES(salary10), salary11 = VALUES(salary11),
      salary12 = VALUES(salary12), salary13 = VALUES(salary13),
      salary14 = VALUES(salary14), no_trade = VALUES(no_trade),
      last_year_team_option = VALUES(last_year_team_option),
      last_year_player_option = VALUES(last_year_player_option),
      last_year_vesting_option = VALUES(last_year_vesting_option),
      opt_out = VALUES(opt_out);

  INSERT IGNORE INTO players_salary_history (player_id, team_id, year, salary)
  SELECT s.player_id, s.team_id, s.year, s.salary
  FROM staging.players_salary_history s
  INNER JOIN players p ON s.player_id = p.player_id
  WHERE s.year != 0;

  INSERT INTO players_service_time (
      player_id, mlb_service_years, mlb_service_days,
      pro_service_years, has_received_arbitration
  )
  SELECT
      s.player_id, s.mlb_service_years, s.mlb_service_days,
      s.pro_service_years, s.has_received_arbitration
  FROM staging.players_roster_status s
  INNER JOIN players p ON s.player_id = p.player_id
  ON DUPLICATE KEY UPDATE
      mlb_service_years = VALUES(mlb_service_years),
      mlb_service_days = VALUES(mlb_service_days),
      pro_service_years = VALUES(pro_service_years),
      has_received_arbitration = VALUES(has_received_arbitration);
  ```

- Verified against a real dump: ran `flask --app app update-db` against
  `dump_2025_yearly` from the `TEST.lg` save, on a throwaway MariaDB
  container (not the persistent `mariadb_data` volume). Result: 15884 rows
  each in `players_contract`/`players_service_time` (1088 with a real
  active salary), 3833 dated rows in `players_salary_history`. No errors;
  row counts consistent with 0053's sampling. Re-verified again after
  dropping `players_contract_extension` — identical row counts for the
  three remaining tables, extension table absent from the schema
  entirely.

**Files involved:**
- `backend/app/db/staging.py` (modified — `DUMP_INCLUSION_LIST`)
- `backend/app/db/sql_scripts/migration/migration_long.sql` (modified)
