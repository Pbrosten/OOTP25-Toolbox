# 0053 — Contract/salary/service-time schema

- **Tag:** feat
- **Status:** Closed
- **Depends on:** —
- **Blocks:** [0054](0054-contract-service-time-migration.md)

## 1. Problem

[0041](0041-trade-target-finder.md) and [0042](0042-contract-arbitration-analyzer.md)
both flagged the same gap: no contract, salary, or years-of-control table
exists anywhere in `staging` or `ootp`. Neither ticket can build its
contract-dependent scope without an `ootp`-schema home for this data first.

This ticket resolves that gap by inspecting a real dump export (`TEST.lg`
save, `dump_2025_yearly` heap) rather than guessing at column names, the same
way [0024](0024-pitcher-schema-ratings-tables.md) did for pitcher ratings.

## 2. Design choices

- **What does staging actually contain?** Four relevant tables, confirmed
  against the real dump:
  - `players_contract` (44 columns, 1775 rows in the sample heap) — the
    active contract: `player_id`, `team_id`, `contract_team_id`,
    `season_year`, a 15-year salary schedule (`salary0`..`salary14`),
    `years`, `current_year`, option flags (`last_year_team_option`,
    `last_year_player_option`, `last_year_vesting_option`, and `next_*`
    variants), `no_trade`, `opt_out`, `opt_out_relegation`, `retained`, plus
    PA/IP incentive-bonus columns (`minimum_pa`, `minimum_pa_bonus`,
    `mvp_bonus`, `cyyoung_bonus`, `allstar_bonus`, etc.). Real sample row:
    player 5, team 18, `salary0..salary5` = 22M/27M/27M/27M/27M/27M,
    `years`=6, `current_year`=3.
  - `players_contract_extension` — identical 44-column shape. In the sample
    heap all 1856 rows have `salary0..salary14` = 0 despite non-zero
    `player_id`/`team_id`/`season_year` fields. Unclear from this single
    save snapshot whether OOTP ever populates real extension-offer salary
    figures here or this table only fills in during an active
    extension-negotiation window this save wasn't in. **Outstanding** — see
    below.
  - `players_salary_history` (`player_id`, `team_id`, `year`, `salary`,
    `uniform`) — historical actual salary paid. Most players have a
    `year=0, salary=0` placeholder row (e.g. `(1, 0, 0, 0, 33)`) alongside
    real dated rows for years they were actually paid (e.g.
    `(5, 18, 2024, 27000000, 55)`).
  - `players_roster_status` (38 columns) — mostly waiver/DL/trade-status
    bookkeeping out of scope for this epic, but carries the years-of-control
    signal neither ticket had found yet: `mlb_service_years`,
    `mlb_service_days`, `pro_service_years`, `pro_service_days`, and
    `has_received_arbitration` (boolean-ish TINYINT). Real sample row:
    player 5 has `mlb_service_years`=10, `has_received_arbitration`=0.
  - Confirmed via `ls` across `dump_2025_01/06/12` and `dump_2026_02`: none
    of these four files appear in monthly ("short") heaps, only in yearly
    ones — same cadence as `players`/`teams` themselves.
- **Full mirror vs. trimmed set?** Same question 0024 faced. `players_contract`
  and `players_contract_extension`'s incentive-bonus columns
  (`minimum_pa`/`minimum_pa_bonus`/`minimum_ip`/`minimum_ip_bonus`/
  `mvp_bonus`/`cyyoung_bonus`/`allstar_bonus`/`*_option_buyout`), `position`,
  `role`, `is_major`, `league_id`, `contract_league_id`, `retained`, and
  `opt_out_relegation` have no consumer in either 0041's filter/rank scope
  or 0042's surplus-value scope. `players_roster_status`'s waiver/DL/trade
  columns are entirely unrelated to contracts. **Chosen:** trim to what
  0041/0042 actually need — salary schedule, years/current_year, no-trade
  and option flags, opt-out, and the service-time/arbitration fields.
  Consistent with 0024's precedent and this project's stated aversion to
  speculative unused columns. `contract_team_id` (the paying team, which can
  differ from the roster team_id under salary retention) is also trimmed for
  now — retained-salary trade scenarios are out of either ticket's stated
  scope.
- **Current-state table vs. dated snapshot (like `players_rating`)?**
  **Chosen: current-state**, upserted on each yearly-heap run — matching how
  `players`/`teams` themselves are handled in `migration_long.sql` (`INSERT
  ... ON DUPLICATE KEY UPDATE`), not how `players_rating` is (append-only,
  dated). Two reasons: (1) contract/roster_status files only ever appear in
  yearly heaps, so there's no higher-frequency signal to preserve between
  snapshots; (2) the multi-year `salary0..salary14` array is already a
  self-describing forward schedule, and `players_salary_history` is already
  a historical ledger keyed by `(player_id, year)` — neither needs a second
  layer of per-heap dating on top.
- **Table names.** `players_contract`, `players_contract_extension`, and
  `players_salary_history` reuse the staging names directly (matches
  existing convention, e.g. `players_batting`/`players_pitching`). The
  service-time subset gets a new, narrower name — `players_service_time` —
  rather than `players_roster_status`, since only ~5 of that table's 38
  columns are being ingested and the full name would misrepresent the
  table's actual (trimmed) contents.
- **Outstanding — `players_contract_extension` semantics unverified.**
  Ingesting it now (same trimmed shape as `players_contract`) is cheap and
  matches 0042's Approach, which explicitly wants extension-scenario
  modeling. But since every sampled row has a zero salary schedule, its
  actual populated shape (what a real pending extension offer looks like)
  isn't confirmed. If [0054](0054-contract-service-time-migration.md)'s
  migration also finds zero non-zero rows across all available yearly
  heaps, flag it back here rather than silently shipping an always-empty
  table.

## 3. Approach

Add to `schema.sql`, alongside the existing ratings tables:

```sql
CREATE TABLE players_contract (
  player_id INT PRIMARY KEY,
  team_id INT,
  season_year INT,
  years SMALLINT,
  current_year SMALLINT,
  salary0 INT, salary1 INT, salary2 INT, salary3 INT, salary4 INT,
  salary5 INT, salary6 INT, salary7 INT, salary8 INT, salary9 INT,
  salary10 INT, salary11 INT, salary12 INT, salary13 INT, salary14 INT,
  no_trade BOOLEAN,
  last_year_team_option BOOLEAN,
  last_year_player_option BOOLEAN,
  last_year_vesting_option BOOLEAN,
  opt_out SMALLINT,
  FOREIGN KEY (player_id) REFERENCES players(player_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE players_contract_extension (
  player_id INT PRIMARY KEY,
  team_id INT,
  season_year INT,
  years SMALLINT,
  current_year SMALLINT,
  salary0 INT, salary1 INT, salary2 INT, salary3 INT, salary4 INT,
  salary5 INT, salary6 INT, salary7 INT, salary8 INT, salary9 INT,
  salary10 INT, salary11 INT, salary12 INT, salary13 INT, salary14 INT,
  no_trade BOOLEAN,
  last_year_team_option BOOLEAN,
  last_year_player_option BOOLEAN,
  last_year_vesting_option BOOLEAN,
  opt_out SMALLINT,
  FOREIGN KEY (player_id) REFERENCES players(player_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE players_salary_history (
  player_id INT,
  team_id INT,
  year SMALLINT,
  salary INT,
  PRIMARY KEY (player_id, year),
  FOREIGN KEY (player_id) REFERENCES players(player_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE players_service_time (
  player_id INT PRIMARY KEY,
  mlb_service_years SMALLINT,
  mlb_service_days SMALLINT,
  pro_service_years SMALLINT,
  has_received_arbitration BOOLEAN,
  FOREIGN KEY (player_id) REFERENCES players(player_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

Add corresponding `DROP TABLE IF EXISTS` lines to the top of `schema.sql`,
in dependency order (before `players`, after any table that FKs onto these —
none currently do).

Migration ingestion (staging → ootp) is scoped separately in
[0054](0054-contract-service-time-migration.md).

**Files involved:**
- `backend/app/db/sql_scripts/schema.sql` (modified — add 4 tables + drops)
