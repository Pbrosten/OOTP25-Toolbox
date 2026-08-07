# 0020 — Resolve unused STATEMENT_RE / naive statement splitting

- **Tag:** chore
- **Status:** Closed
- **Depends on:** —
- **Blocks:** —

## 1. Problem

A quote-aware statement-splitting regex (`STATEMENT_RE`,
`backend/app/db/staging.py:18`) is defined but dead — the real splitting
logic in `sql_dump_to_staging()` (`staging.py:78`) is a simpler heuristic
(`line.strip().endswith(";")`), fine for standard
one-statement-per-line `mysqldump` output but would mis-split a line
containing multiple `;`-terminated statements. `connect_staging_db()` also
doesn't set `client_flag=CLIENT_MULTI_STATEMENTS`, so this isn't currently
exercised either way for OOTP's export format specifically.

## 2. Design choices

- **Delete vs. actually use it.** Options considered: (a) delete
  `STATEMENT_RE` and document the line-based-splitting assumption it was
  meant to harden against; (b) wire it into `sql_dump_to_staging()` for
  robustness against edge-case dump formatting. **Chosen: (a)** — OOTP's
  `mysqldump`-style exports are one-statement-per-line by construction (this
  is how the pipeline has worked in production use so far), and the
  simpler, already-battle-tested line-based splitter is easier to reason
  about than a quote-aware regex that has never actually run. If a dump file
  is ever found that violates the one-statement-per-line assumption, that's
  a concrete bug report that can drive re-adding statement-aware splitting
  with a regression fixture, rather than speculatively hardening against an
  unobserved case now.

## 3. Approach

- Delete `STATEMENT_RE` (`backend/app/db/staging.py:18`) and its now-unused
  `re` import if nothing else in the file needs it.
- Add a short comment above `sql_dump_to_staging()`'s line-based split
  documenting the one-statement-per-line assumption it relies on, so a
  future change doesn't have to rediscover why the simpler approach was
  chosen.

**Files involved:**
- `backend/app/db/staging.py` (modified)
