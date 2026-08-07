# 0019 — Fix malformed logger.debug call in update_player_age

- **Tag:** fix
- **Status:** Open
- **Depends on:** —
- **Blocks:** —

## 1. Problem

`logger.debug(current_date, birth_date)` (`backend/app/db/update.py:72`)
passes a non-string `date` object as the log message and `birth_date` as a
positional `%`-format arg. Currently dormant because the root logger is
configured at `INFO` (`backend/app/__init__.py:21-24`), so `.debug()`
short-circuits before formatting. If debug logging is ever enabled for this
logger, `LogRecord.getMessage()` raises `TypeError`, aborting
`update_player_age()` mid-batch — and since that function commits every 500
rows (`update.py:77-82`), not once at the end, some ages would already be
persisted before the crash.

## 2. Design choices

Chosen approach, no real alternatives considered: fix the call signature —
removing the line entirely was also considered but the log statement is
harmless and potentially useful once correctly formatted, so fixing beats
deleting.

## 3. Approach

- Change `backend/app/db/update.py:72` from
  `logger.debug(current_date, birth_date)` to
  `logger.debug("current_date=%s birth_date=%s", current_date, birth_date)`.

**Files involved:**
- `backend/app/db/update.py` (modified)
