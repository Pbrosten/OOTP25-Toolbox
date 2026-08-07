# 0018 — Remove vestigial SQLite converter registration

- **Tag:** chore
- **Status:** Open
- **Depends on:** —
- **Blocks:** —

## 1. Problem

`register_converters()` (`backend/app/db/connection.py:40-44`) calls
`sqlite3.register_converter("timestamp", ...)` — a leftover from a
pre-MariaDB-migration version of the app, called unconditionally from
`backend/app/db/__init__.py::init_app()`. No `sqlite3` connection is opened
anywhere in the current pipeline. Harmless but dead code, and its
corresponding test
(`test_connection.py::test_register_converters_registers_timestamp`) is
testing that dead code rather than anything load-bearing.

## 2. Design choices

Chosen approach, no real alternatives considered: delete outright. No
current or planned code path uses `sqlite3`, so there's nothing to preserve
behavior for.

## 3. Approach

- Delete `register_converters()` from `backend/app/db/connection.py` and its
  `sqlite3`/`datetime` imports if unused elsewhere in the file.
- Remove its call site in `backend/app/db/__init__.py::init_app()`.
- Delete `test_connection.py::test_register_converters_registers_timestamp`
  (or fold into [0017](0017-rewrite-stale-pipeline-tests.md)'s pass over
  the same file, if that lands first).

**Files involved:**
- `backend/app/db/connection.py` (modified)
- `backend/app/db/__init__.py` (modified)
- `backend/tests/db/test_connection.py` (modified)
