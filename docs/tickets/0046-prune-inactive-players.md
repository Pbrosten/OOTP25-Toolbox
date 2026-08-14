# 0046 — Prune players inactive before 2024; filter them at ingestion

- **Tag:** chore
- **Status:** In-Progress
- **Depends on:** —
- **Blocks:** —

## 1. Problem

`migration_long.sql`'s `INSERT INTO players` (lines 31-46) has no activity
filter at all — every row in `staging.players` gets upserted into
`ootp.players` unconditionally. `staging.players` mirrors the OOTP save's
full player pool: [0029](0029-pitcher-pitch-repertoire.md)'s dump inspection
found 134,808 rows in one sample save, "covering every player in the save's
history, not just active rosters." This app's stated product goal
(`docs/improvements/expanded-functionality.md`) is current-day GM
decision-support, not a full league-history archive.

Two concrete symptoms:
- Long-retired/historical players clutter search results — `players.py`'s
  `/search` (lines 59-88) matches on name only, no activity filter, so an
  old flavor-text player sharing a surname competes with current rosters.
- These players break the percentiles page: `players_rating` snapshots only
  exist from whenever ingestion started, so a player who stopped appearing
  in the league long before that has zero rating rows, and
  `BatterPercentiles`/`PitcherPercentiles` have no explicit handling for
  "this player has no ratings at all" — they either render empty or error,
  with nothing telling the user why.

## 2. Design choices

- **Outstanding — what data defines "active before 2024."** Neither
  `ootp.players` nor `staging.players` (as currently ingested, per
  `DUMP_INCLUSION_LIST` in `backend/app/db/staging.py:9-16`) has a
  last-active-year or debut/quit-year column. The closest available signal
  is `MAX(year)` across `players_career_batting_stats`/
  `players_career_pitching_stats`, but for an ingestion-time filter that has
  to be read from `staging.players_career_batting_stats`/
  `_pitching_stats` — the raw staging copy — since it needs to run *before*
  the `players` INSERT decides whether to include a row (chicken-and-egg
  against `ootp`'s own copy, which only has rows for players already
  inserted). Whether OOTP's raw `players.mysql` export carries a more direct
  field (a retirement/quit year) isn't known — needs inspecting a real dump
  export the way [0029](0029-pitcher-pitch-repertoire.md) did for
  `players_pitching`'s per-pitch columns, rather than assumed here.
- **Outstanding — hard delete vs. archive flag.** The alternative to
  physically deleting old players is extending
  [0011](0011-retired-player-flag.md)'s `retired` flag with an
  `archived`/`inactive`-style column that just excludes them from search and
  percentiles without removing rows — safer, reversible, and sidesteps the
  FK problem below. Not decided.
- **Outstanding — FK cascade.** Checked `schema.sql`: no table anywhere
  declares `ON DELETE CASCADE` (every `FOREIGN KEY` is default
  RESTRICT/NO ACTION). A real `DELETE FROM players` would fail today against
  `players_rating`, `players_career_batting_stats`,
  `players_career_pitching_stats`, and every rating-detail table chained off
  `players_rating`'s `rating_id`, unless rows are deleted in dependency
  order first or those FKs are changed to cascade. This needs resolving
  regardless of the hard-delete-vs-archive choice above, since even an
  archive flag doesn't remove the need to decide how deletes *would* work if
  ever needed.
- **Outstanding — exact 2024 cutoff semantics.** Assumed here as "no
  career-stat row with `year >= 2024`," but a save's in-game calendar year
  may not track real-world time depending on when it was started — confirm
  once the "what data defines active" question above is resolved.
- **Resolved — scope.** This is two linked pieces of work, not one: a
  one-time prune of whatever's already in the live `ootp` database, and an
  ongoing ingestion-time filter in `migration_long.sql` so future long-heap
  runs don't reintroduce the same players. Per this project's standing rule
  on database changes, the one-time prune must be verified against a
  throwaway DB copy first and only run against the real `ootp` database with
  explicit user confirmation — it is not something to execute unasked once
  implemented.

## 3. Approach (needs the Outstanding questions resolved before implementation)

- Ingestion filter: extend `migration_long.sql`'s `players` INSERT with a
  `WHERE`/`NOT EXISTS` clause excluding players whose most recent
  `staging.players_career_batting_stats`/`players_career_pitching_stats`
  year is before 2024 (exact predicate depends on the Outstanding data-source
  question above).
- One-time prune: a script (not necessarily a Flask CLI command — could be a
  one-off SQL script, run manually) that removes players matching the same
  cutoff from the already-populated `ootp` database, handling FK dependency
  order (or relying on `ON DELETE CASCADE` if that's added to `schema.sql`
  as part of this ticket).
- Worth a quick look at `players_similarity` (`schema.sql:406-412`) while
  touching this — it's the one table with no `ENGINE=InnoDB`/FK declaration
  at all and may be unrelated vestigial content, not a cascade target.

**Files involved:**
- `backend/app/db/sql_scripts/migration/migration_long.sql` (modified)
- `backend/app/db/sql_scripts/schema.sql` (possibly modified, if cascade
  behavior is added)
- A new one-time prune script (new file, path TBD)
