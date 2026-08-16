# Ticket Index

Tracks planned/in-progress/completed work for OOTP25-Toolbox. Each ticket is a
markdown file in this directory named `NNNN-short-slug.md`, containing: the
problem it solves, design choices (including outstanding/undecided ones), the
chosen approach and files involved, a tag, and a status.

**Tags:** `feat` | `fix` | `chore` | `refactor`
**Statuses:** `Open` | `In-Progress` | `Closed`

New tickets should start from [TEMPLATE.md](TEMPLATE.md) and be added to the
table below (and any relevant epic section) once created.

## Epic: Admin DB operations as API endpoints

Motivated by repeated local friction running `flask --app app init-db` /
`update-db` from the host `.venv` (host can't resolve the `mariadb` container
hostname or see `/data/dumps`, requiring manual env-var overrides every time).
Exposing the same operations as backend routes runs them inside the container
with correct config by construction, and additionally allows triggering them
from a `curl` request or a future UI button.

Suggested order: 0001 → 0002 → 0003 → 0004 → 0005. 0006 split off from 0005's
design discussion (log-tail progress needs backend work 0004 didn't do).

```
[x] 0001 DB service layer
      |
      v
[x] 0002 Admin API endpoints
      |
      +----------------------------+
      v                            |
[x] 0003 Auth guard                |
      |                            |
      v                            v
[x] 0004 Async update-db job <-----+
      |
      v
[x] 0005 Frontend trigger
      |
      v
[x] 0006 Job log capture

[x] = Closed   [ ] = Open   [~] = In-Progress
```

| # | Title | Tag | Status | Depends on |
|---|-------|-----|--------|------------|
| [0001](0001-extract-db-service-layer.md) | Extract DB init/update logic into a reusable service layer | refactor | Closed | — |
| [0002](0002-admin-api-endpoints.md) | Admin API endpoints for init-db and update-db | feat | Closed | 0001 |
| [0003](0003-admin-api-auth-guard.md) | Guard admin endpoints with access control | feat | Closed | 0002 |
| [0004](0004-async-update-db-job.md) | Run update-db as an async background job with status polling | feat | Closed | 0002, 0003 |
| [0005](0005-frontend-admin-trigger.md) | Frontend trigger for admin DB operations | feat | Closed | 0004 |
| [0006](0006-job-log-capture.md) | Capture per-line logs for update-db jobs | feat | Closed | 0004, 0005 |

## Backend pipeline improvements

Sourced from [docs/improvements/README.md](../improvements/README.md), a
review of the SQL dump ingestion/processing pipeline. Unlike the epic above,
these are largely independent — no fixed implementation order — except where
noted in a ticket's own Design choices section (e.g. 0014/0015 are
alternatives, not a sequence; 0021 folds into 0022).

| # | Title | Tag | Status | Depends on |
|---|-------|-----|--------|------------|
| [0007](0007-persist-processed-heaps.md) | Track processed heaps so update-db only ingests what's new | feat | Closed | — |
| [0008](0008-fix-prod-config-and-secret-logging.md) | Derive is_production from env; stop printing config with secrets | fix | Closed | — |
| [0009](0009-scope-ratings-detail-inserts-to-heap-date.md) | Scope ratings-detail inserts to the current heap date | fix | Closed | — |
| [0010](0010-cli-update-db-in-flight-lock.md) | Guard the CLI update-db path with the same in-flight-job lock as the API | fix | Closed | — |
| [0011](0011-retired-player-flag.md) | Add a `retired` flag so frozen player data is visible, not silent | feat | Closed | — |
| [0012](0012-projection-worker-app-context.md) | Stop relying on fork() semantics for Flask context in projection workers | refactor | Closed | — |
| [0013](0013-reenable-staging-reset.md) | Re-enable the staging DB reset before each load | chore | Closed | — |
| [0014](0014-drop-unused-pitching-ingestion.md) | Stop ingesting players_pitching until something reads it | chore | Closed | — |
| [0015](0015-pitcher-projection-epic.md) | Pitcher projections: schema, migration, and projection pipeline | feat | Closed | — |
| [0016](0016-update-db-row-count-visibility.md) | Report row counts actually written by update-db | feat | Closed | — |
| [0017](0017-rewrite-stale-pipeline-tests.md) | Rewrite or remove 16 stale pipeline tests | chore | Closed | — |
| [0018](0018-remove-vestigial-sqlite-converter.md) | Remove vestigial SQLite converter registration | chore | Closed | — |
| [0019](0019-fix-malformed-logger-debug-call.md) | Fix malformed logger.debug call in update_player_age | fix | Closed | — |
| [0020](0020-unused-statement-re-regex.md) | Resolve unused STATEMENT_RE / naive statement splitting | chore | Closed | — |
| [0021](0021-fetch-projection-inputs-cursor-scope.md) | Fetch projection inputs inside the cursor's with block | refactor | Closed | — |
| [0022](0022-consolidate-run-script-boilerplate.md) | Consolidate repeated run-script/rollback/commit boilerplate | refactor | Closed | — |
| [0030](0030-exclude-pitchers-from-batting-projection.md) | Exclude pitchers from the batting projection workflow (pending a future TWP tag) | fix | Closed | — |
| [0046](0046-prune-inactive-players.md) | Prune players inactive before 2024; filter them at ingestion | chore | Closed | — |
| [0049](0049-fix-test-players-mock-pattern.md) | Fix broken DB-connection mocks in `tests/api/test_players.py` | chore | Closed | — |
| [0055](0055-fix-semicolon-in-comment-breaks-migration-short.md) | Fix semicolon inside a comment breaking `migration_short.sql` | fix | Closed | — |
| [0066](0066-recalibrate-run-value-constants-per-save.md) | Recalibrate run-value constants against this save's own league, not a fixed real-MLB baseline | fix | Open | — |
| [0067](0067-two-way-player-detection.md) | Two-way player (TWP) detection and dual-sided pitching ingestion | feat | Closed | — |

## Epic: Pitcher projections

[0015](0015-pitcher-projection-epic.md) was filed as a large epic outline
rather than a scoped plan (see its Design choices section). Broken down here
into per-subsystem tickets the way the admin-API epic was split into
0001–0006. Mostly sequential — each stage's column shapes depend on the
previous stage existing, and 0026 (methodology) and 0028 (value/WAR) are
genuinely open design questions blocking implementation — except that the
line forks after 0025: pitch-repertoire storage (0029) shares the same
staging source but is independent of the projection-methodology/value/API
line, since neither of its consumers (an analytics report, long-term
projection refinement) depends on that line's output. 0034 is the first of
that "long-term projection refinement" consumer 0029 anticipated — it
depends on 0029's data existing but, like 0026/0028, is blocked on an open
design question (how "combined pitch-category quality" becomes a run-value
number) — resolved as a proportional-share approximation off the existing
aggregate `pitching_runs`, see 0034's Design choices. [0035](0035-pitcher-career-stats-page.md)
is a separate branch off nothing in the diagram below — it mirrors
`players_career_batting_stats` / `PlayerDetails.vue`'s batting table with raw
per-season box-score counting stats (W/L/ERA/G/GS/SV/IP/SO/WHIP), independent
of the ratings/projection pipeline (0025–0028) and of pitch repertoire (0029).
[0036](0036-fastball-velocity-display.md) is likewise independent — it reads
the existing `players_pitching.velocity` column (already ingested by 0025)
and surfaces it as a display-only MPH band next to the Fastball Velo
percentile bar. [0037](0037-split-sp-rp-percentile-cohorts.md) depends on
0027 directly — it's a cohort-scoping fix to the same percentile query 0027
built, not a new data source.

```
[x] 0015 Epic tracker
      |
      v
[x] 0024 Schema (players_pitching / players_pitching_talent)
      |
      v
[x] 0025 Migration ingestion (staging -> ootp)
      |
      +----------------------------------+
      v                                  v
[x] 0026 Projection methodology    [x] 0029 Pitch repertoire (epic tracker)
    + PitcherProjection                  |
      |                                  v
      v                            [x] 0031 Schema (players_pitch_repertoire)
[x] 0028 Run-value / WAR                 |
      |                                  v
      v                            [x] 0032 Migration (staging -> ootp)
[x] 0027 API route +                     |
    PitcherPercentiles frontend          v
                                    [x] 0033 API route + report component
                                          |
                                          v
                                    [x] 0034 Fastball/Breaking/Offspeed
                                        run-value percentiles

[x] = Closed   [ ] = Open   [~] = In-Progress
```

| # | Title | Tag | Status | Depends on |
|---|-------|-----|--------|------------|
| [0015](0015-pitcher-projection-epic.md) | Pitcher projections: schema, migration, and projection pipeline (epic tracker) | feat | Closed | — |
| [0024](0024-pitcher-schema-ratings-tables.md) | Pitcher ratings schema: `players_pitching` / `players_pitching_talent` | feat | Closed | — |
| [0025](0025-pitcher-migration-ingestion.md) | Ingest pitcher ratings: re-enable staging load + `migration_short.sql` | feat | Closed | 0024 |
| [0026](0026-pitcher-projection-methodology.md) | Pitcher projection methodology + `PitcherProjection` class | feat | Closed | 0025 |
| [0028](0028-pitcher-run-value-war.md) | Pitcher run-value/WAR: methodology, schema, and projection wiring | feat | Closed | 0026 |
| [0027](0027-pitcher-api-frontend-wiring.md) | Pitcher projections API route + `PitcherPercentiles` component | feat | Closed | 0026, 0028 |
| [0029](0029-pitcher-pitch-repertoire.md) | Pitcher pitch repertoire: number of pitches + per-pitch quality (epic tracker) | feat | Closed | 0025 |
| [0031](0031-pitch-repertoire-schema.md) | Pitch repertoire schema: `players_pitch_repertoire` | feat | Closed | 0025 |
| [0032](0032-pitch-repertoire-migration.md) | Ingest pitch repertoire: `migration_short.sql` | feat | Closed | 0031 |
| [0033](0033-pitch-repertoire-report.md) | Pitch repertoire API route + report component | feat | Closed | 0032 |
| [0034](0034-pitch-type-run-value-percentiles.md) | Per-pitch-category run-value percentiles: Fastball / Breaking / Offspeed | feat | Closed | 0029 |
| [0035](0035-pitcher-career-stats-page.md) | Pitcher career stats table (mirror batter career stats) | feat | Closed | — |
| [0036](0036-fastball-velocity-display.md) | Fastball velocity display on pitcher player pages | feat | Closed | — |
| [0037](0037-split-sp-rp-percentile-cohorts.md) | Split SP/RP percentile cohorts (stop comparing starters to relievers) | fix | Closed | 0027 |

## Epic: GM Tools

Sourced from [docs/improvements/expanded-functionality.md](../improvements/expanded-functionality.md)'s
Tier 1 #1, #2, #3, #5, #6, #7 and Tier 2 #12 — the full slate of GM-facing
analysis tools tagged `stagged` there. Previously filed under five separate
epic headings; merged into one, since the tools overlap more than they
divide: two data gaps (no minor-league level/affiliate data; no
contract/salary/arbitration data anywhere in `staging`/`ootp`) block or
partially block five of the seven, and several tools consume each other's
output (Command Center aggregates Roster Optimization + Prospect Pipeline +
Contract Analyzer; Prospect Pipeline reuses Player Development Monitor's
trend layer; Defensive Optimization reuses Roster Optimization's query
layer).

`### Tool` subsections below are ordered by build recommendation — gated by
data readiness, not by the epic's original grouping:

1. **Player Development Monitor** (0044) — zero data gaps, ships first.
2. **Trade Target Finder** (0041) reduced v1 — position/age/WAR/role
   filtering ships now; full scope waits on contract data (step 7).
3. **Roster Optimization & Organizational Depth** (0039) — now ships as
   one full-scope pass, not split into MLB-only/org-depth halves: the
   level/affiliate data gap from step 5 turned out to be a small
   schema+migration addition ([0062](0062-team-level-affiliate-schema-migration.md)),
   not a real blocker, so it's filed as a direct prerequisite rather than
   deferring org-depth to later.
4. **Defensive Optimization** (0040) — follows 0039, reuses its shared
   query layer with a defense-weighted variant.
5. *(prerequisite)* — inspect a real dump export for minor-league
   level/affiliate fields and contract/salary/arbitration tables; file
   schema + migration tickets mirroring
   [0024](0024-pitcher-schema-ratings-tables.md)/[0025](0025-pitcher-migration-ingestion.md).
   Contract/salary/service-time half is filed as
   [0053](0053-contract-service-time-schema.md)/
   [0054](0054-contract-service-time-migration.md), both closed;
   minor-league level/affiliate half is now filed as
   [0062](0062-team-level-affiliate-schema-migration.md) (needed for
   steps 6, 8). Unblocks steps 6–8.
6. **Prospect Pipeline** (0043) — level/affiliate data from step 5 now
   closed (0062/0063), reuses 0044's trend layer from step 1, and its own
   FV/value methodology (FanGraphs Future Value framework, replicated
   against this app's ratings data) is broken into
   [0068](0068-prospect-fv-value-calculation.md)/
   [0069](0069-prospect-query-layer-api.md)/
   [0070](0070-prospect-pipeline-frontend.md) — Closed.
7. **Contract & Arbitration Analyzer** (0042) — needs contract/salary data
   from step 5; no reduced-scope fallback exists.
8. **Trade Target Finder** (0041) full scope — layers in contract/injury/
   organizational-fit filters once step 5's data and 0039's depth-chart
   output exist.
9. **GM Command Center** (0038) — aggregates 0039 + 0042 + 0043 output, so
   it has the least value built first; sequenced last. Also needs its own
   "current team" concept resolved (no session/team-selection exists
   anywhere in the app today) — see 0038's Design choices.

Ticket-level dependency graph (matches the table's "Depends on" column
below; step-5's contract/salary/service-time half is filed as 0053/0054,
its minor-league level/affiliate half as 0062, both drawn below):

```
[x] 0044 Player Development Monitor
      |
      v
[~] 0043 Prospect Pipeline (epic tracker) --------+
      |                                          |
      v                                          |
[x] 0068 Prospect FV/value calculation             |
      |                                          |
      v                                          |
[x] 0069 Prospect query layer + API               |
      |                                          |
      v                                          |
[x] 0070 Prospect Pipeline frontend               |
                                                  |
[x] 0062 Team level/affiliate schema+migration    |
      |                                          |
      v                                          |
[x] 0063 Roster depth-chart query + API           |
      |                                          |
      v                                          |
[x] 0064 Roster depth-chart frontend              |
      |                                          |
      v                                          |
[x] 0039 Roster Optimization & Org Depth --------+
      |                                          |
      v                                          |
[ ] 0040 Defensive Optimization                  |
                                                  |
[x] 0053 Contract/service-time schema             |
      |                                          |
      v                                          |
[x] 0054 Contract/service-time migration          |
      |                                          |
      v                                          |
[x] 0056 Surplus-value calculation                |
      |                                          |
      v                                          |
[x] 0057 Surplus-value frontend display           |
      |                                          |
      v                                          |
[x] 0058 Recommendation thresholds                |
      |                                          |
      v                                          |
[x] 0059 Wire injury risk into surplus value      |
      |                                          |
      v                                          |
[x] 0042 Contract & Arbitration Analyzer --------+
                                                  |
                                                  v
                                       [ ] 0038 GM Command Center

[ ] 0041 Trade Target Finder — standalone, omitted above (reduced v1 has no
    ticket dependencies; full-scope layering is data/output-gated per the
    build-order list, not a hard ticket dependency — same convention as
    0035/0036/0037 being left out of the pitcher-projection epic's diagram).

[ ] 0065 GM Org Selection + Theming — standalone, omitted above (resolves
    the "current team" gap 0038/0039 both flagged, but scoped narrowly to
    selection + theming, not the full Command Center dashboard; no ticket
    depends on it yet).

[x] = Closed   [ ] = Open   [~] = In-Progress
```

| # | Title | Tag | Status | Depends on |
|---|-------|-----|--------|------------|
| [0044](0044-player-development-monitor.md) | Player Development Monitor (epic tracker) | feat | Closed | — |
| [0041](0041-trade-target-finder.md) | Trade Target Finder (epic tracker) | feat | Open | — |
| [0039](0039-roster-optimization-org-depth.md) | Roster Optimization & Organizational Depth (epic tracker) | feat | Closed | 0062 |
| [0040](0040-defensive-optimization.md) | Defensive Optimization (epic tracker) | feat | Open | 0039 |
| [0043](0043-prospect-pipeline.md) | Prospect Pipeline (epic tracker) | feat | In-Progress | 0044 |
| [0042](0042-contract-arbitration-analyzer.md) | Contract & Arbitration Analyzer (epic tracker) | feat | Closed | 0053, 0054 |
| [0038](0038-gm-command-center.md) | GM Command Center (epic tracker) | feat | Open | 0039, 0042, 0043 |
| [0065](0065-gm-org-selection-theming.md) | GM organization selection + app-wide color theming | feat | Open | — |

### Tool: Player Development Monitor

[0044](0044-player-development-monitor.md) — the only epic whose core scope
(tracking rating changes across existing per-heap snapshots) needs zero new
data ingestion. Its "meaningful change" threshold design question is
resolved (see 0044's Design choices) and broken into three sub-tickets. Its
trend-computation layer, once built, is a direct input to Prospect Pipeline
below.

| # | Title | Tag | Status | Depends on |
|---|-------|-----|--------|------------|
| [0050](0050-rating-trend-query-layer.md) | Rating delta/trend query layer + API route | feat | Closed | — |
| [0051](0051-development-alert-generation.md) | Development alert generation (narrative rule layer) | feat | Closed | 0050 |
| [0052](0052-development-monitor-frontend.md) | Frontend trend/alert display (PlayerDetails.vue) | feat | Closed | 0050, 0051 |

### Tool: Trade Target Finder

[0041](0041-trade-target-finder.md) — ships in two passes. A reduced v1
(filter/rank by position, age, projected WAR, and role) is buildable today
with no new ingestion, so it can ship alongside Player Development Monitor.
The full scope (contract status, salary, years-of-control, injury risk,
team-competitiveness, organizational fit) waits on the contract/salary
ingestion prerequisite and, for organizational fit, on Roster Optimization's
depth-chart output.

### Tool: Roster Optimization & Organizational Depth

[0039](0039-roster-optimization-org-depth.md) — ships as one full-scope
pass (MLB roster + AAA/AA/A/Rookie affiliates together), not split into
an MLB-only slice first: inspecting a real `TEST.lg` dump export found
`teams.parent_team_id`/`level` already present in the raw OOTP export, so
the org-depth gap is a small schema+migration ticket
([0062](0062-team-level-affiliate-schema-migration.md)) rather than a real
blocker. The depth chart itself is
[0063](0063-roster-depth-chart-query-api.md) (query layer + API, grouped
by org/level/position, pitchers split SP/RP) and
[0064](0064-roster-depth-chart-frontend.md) (frontend view). The "best
9-man lineup" optimizer from the source doc is deliberately deferred,
unticketed — see 0039's Design choices. Whichever of this or Defensive
Optimization starts first builds the shared "WAR by player by eligible
position" query layer the other reuses — sequenced first here since its
output also feeds GM Command Center and Trade Target Finder's
organizational-fit filter.

| # | Title | Tag | Status | Depends on |
|---|-------|-----|--------|------------|
| [0062](0062-team-level-affiliate-schema-migration.md) | Ingest team level and parent-org data | feat | Closed | — |
| [0063](0063-roster-depth-chart-query-api.md) | Roster depth-chart query layer + API route | feat | Closed | 0062 |
| [0064](0064-roster-depth-chart-frontend.md) | Roster depth-chart frontend view | feat | Closed | 0063 |
| [0078](0078-depth-chart-top-prospects-low-levels.md) | Top-10 prospect rankings at A/High-A and Rookie/Complex on the Org Depth Chart | feat | Closed | 0064, 0069 |

0064 deliberately left A/High-A and Rookie/Complex (levels 4/6) as plain
roster-count tiles, since current-ratings WAR wasn't a meaningful ranking
signal that far from MLB-readiness and a real talent-based alternative
would have meant building a whole parallel projection methodology.
[0078](0078-depth-chart-top-prospects-low-levels.md), filed once the
Prospect Pipeline epic supplied exactly that (0068's talent-ceiling FV
calc), replaces those tiles with a real top-10 ranking.

### Tool: Defensive Optimization

[0040](0040-defensive-optimization.md) — sibling of Roster Optimization;
sequenced immediately after it to reuse rather than duplicate the shared
depth-chart query layer with a defense-weighted variant. Needs confirming
that `players_fielding_position` grades are populated across all 9 slots per
player regardless of games actually played there, before scoping
"position-switch scenarios."

### Tool: Prospect Pipeline

[0043](0043-prospect-pipeline.md) — the minor-league level/affiliate gap it
shared with Roster Optimization's org-depth slice is closed (0062/0063),
and its "development trajectory" scope reuses Player Development Monitor's
trend layer (0050) rather than reimplementing snapshot-diffing. Its
prospect-value methodology replicates FanGraphs' Future Value framework
against this app's own talent/current ratings data (full derivation in
0043's Design choices), broken into
[0068](0068-prospect-fv-value-calculation.md) (calc module),
[0069](0069-prospect-query-layer-api.md) (query layer + API), and
[0070](0070-prospect-pipeline-frontend.md) (frontend view) — same
sequential-layering convention as 0050/0051/0052 and 0062/0063/0064. Three
follow-ups filed from a real user review of 0070 against live data:
[0071](0071-align-player-page-surplus-value-with-fv.md) (player-page
surplus value currently shows the 0056 contract-based number, which is
almost always "not available" for a prospect, instead of 0068's FV-based
one), [0072](0072-prospect-risk-adjustment.md) (FV/surplus value/star odds
don't yet discount for a large gap between a prospect's talent ceiling and
current-form ability -- a real risk signal 0068 already computes but
doesn't use for value), and
[0073](0073-prospect-pipeline-org-theming.md) (the Prospect Pipeline page
doesn't yet carry the selected org's real colors the way 0064's depth
chart does). The age gate that same review surfaced (a 32-year-old
optioned-down veteran showing as a "prospect") was small enough to fix
directly rather than file a ticket for -- see 0043/0069's post-close
correction notes. [0074](0074-league-wide-prospect-leaderboard.md) is a
fourth follow-up, requested directly rather than surfaced by a bug report:
a league-wide ranked leaderboard (today's view is org-scoped only), which
reopens 0068's "compute at read time, no new table" decision as its
central open question -- 0069 measured the unfiltered case at ~46s, too
slow for a leaderboard that's unfiltered by definition. Resolved toward
persisting per heap (reversing 0068's call) and broken into
[0075](0075-persist-prospect-value-per-heap.md) (schema + heap-processing
calc, mirrors `players_run_value`'s existing pattern),
[0076](0076-leaderboard-query-layer-api.md) (query layer + `?leaderboard=1`
API mode), and [0077](0077-leaderboard-frontend-view.md) (frontend view) --
same sequential-layering convention as 0068/0069/0070 itself.

| # | Title | Tag | Status | Depends on |
|---|-------|-----|--------|------------|
| [0068](0068-prospect-fv-value-calculation.md) | Prospect FV/value calculation module | feat | Closed | — |
| [0069](0069-prospect-query-layer-api.md) | Prospect query layer + API route | feat | Closed | 0068 |
| [0070](0070-prospect-pipeline-frontend.md) | Prospect Pipeline frontend view | feat | Closed | 0069 |
| [0071](0071-align-player-page-surplus-value-with-fv.md) | Align player-page surplus value with FV-based prospect value | feat | Closed | 0056, 0068 |
| [0072](0072-prospect-risk-adjustment.md) | Risk-adjust FV/surplus value for high-potential/low-overall prospects | feat | Closed | 0068 |
| [0073](0073-prospect-pipeline-org-theming.md) | Org color theming for the Prospect Pipeline page | feat | Closed | 0070 |
| [0074](0074-league-wide-prospect-leaderboard.md) | League-wide prospect leaderboard (epic tracker) | feat | In-Progress | 0069, 0072 |
| [0075](0075-persist-prospect-value-per-heap.md) | Persist prospect FV/value per heap | feat | Closed | — |
| [0076](0076-leaderboard-query-layer-api.md) | Leaderboard query layer + API | feat | Closed | 0075 |
| [0077](0077-leaderboard-frontend-view.md) | Leaderboard frontend view | feat | Closed | 0076 |

### Tool: Contract & Arbitration Analyzer

[0042](0042-contract-arbitration-analyzer.md) — the one tool with no
reduced-scope fallback: "should we pay this player" is meaningless without
knowing what he's currently owed. Its contract/salary/service-time ingestion
prerequisite (shared with [0041](0041-trade-target-finder.md)'s full scope)
is filed as [0053](0053-contract-service-time-schema.md)/
[0054](0054-contract-service-time-migration.md), both closed. The
surplus-value calculation itself is broken into
[0056](0056-surplus-value-calculation.md) (calc module + API,
age-decline/years-of-control model, $/WAR constant derived from real
`TEST.lg` contract data — later corrected twice post-close: a
`current_year` indexing bug and a missing non-decreasing-arbitration
floor, both from real user-reported cases) and
[0057](0057-surplus-value-frontend-display.md) (display, gated off for
free agents). The Extend/Keep/Let-walk/Non-tender/Trade recommendation
label is [0058](0058-contract-recommendation-thresholds.md) — a two-axis
decision table derived from a curated cohort of real, salaried contracts
(deriving from the full player pool failed initially: this save has 259
teams, so most rated players are organizational depth, not a
projection-system bug). [0059](0059-wire-injury-risk-into-surplus-value.md)
closes the last remaining gap — the `prone_overall` injury-risk proxy was
chosen back in 0041/0042 but 0056 never actually applied it.

| # | Title | Tag | Status | Depends on |
|---|-------|-----|--------|------------|
| [0053](0053-contract-service-time-schema.md) | Contract/salary/service-time schema | feat | Closed | — |
| [0054](0054-contract-service-time-migration.md) | Ingest contract/salary/service-time: `migration_long.sql` | feat | Closed | 0053 |
| [0056](0056-surplus-value-calculation.md) | Surplus-value calculation module + API route | feat | Closed | 0053, 0054 |
| [0057](0057-surplus-value-frontend-display.md) | Surplus-value frontend display | feat | Closed | 0056 |
| [0058](0058-contract-recommendation-thresholds.md) | Contract recommendation thresholds | feat | Closed | 0056 |
| [0059](0059-wire-injury-risk-into-surplus-value.md) | Wire injury risk into the surplus-value calculation | feat | Closed | 0056 |

### Tool: GM Command Center

[0038](0038-gm-command-center.md) — a landing dashboard that aggregates
roster weaknesses (Roster Optimization), promotion readiness (Prospect
Pipeline), and contract decisions (Contract & Arbitration Analyzer). Built
last, once those three exist, rather than as an early placeholder shell —
it has no data of its own. Also needs a "current team" concept designed
(session/config value, or route param) before it can scope anything to a
specific GM's roster.

## Frontend / stats display fixes

| # | Title | Tag | Status | Depends on |
|---|-------|-----|--------|------------|
| [0023](0023-fix-career-batting-rate-stats-display.md) | Fix OBP/SLG/OPS in the career batting stats table | fix | Closed | — |
| [0048](0048-batting-career-totals-seasons-label.md) | Replace "Total" with a season count in the batting career stats table | fix | Closed | — |
| [0060](0060-exclude-dh-from-fielding-percentiles.md) | Exclude DH players from fielding percentiles | fix | Closed | — |
| [0061](0061-refetch-player-data-on-route-param-change.md) | Refetch player data when navigating between player pages | fix | Closed | — |

## Search & display refinements

Small, independent frontend/API-behavior tickets — not tied to a specific
epic above.

| # | Title | Tag | Status | Depends on |
|---|-------|-----|--------|------------|
| [0045](0045-remove-mlb-percentile-toggle.md) | Remove the MLB percentile toggle; don't render percentiles for non-MLB players | fix | Closed | — |
| [0047](0047-search-order-by-career-war.md) | Order player search results by career WAR | feat | Closed | — |
