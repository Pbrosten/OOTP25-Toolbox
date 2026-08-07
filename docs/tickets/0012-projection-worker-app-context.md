# 0012 — Stop relying on fork() semantics for Flask context in projection workers

- **Tag:** refactor
- **Status:** Open
- **Depends on:** —
- **Blocks:** —

## 1. Problem

`process_player()` (`backend/app/db/projection.py:27`) calls
`current_app.logger.warning(...)` inside a multiprocessing worker. This only
works because Linux's default `fork()` start method clones the parent's
active app-context state into each child — nothing in the code explicitly
pushes a context in the worker. `project_players()`
(`backend/app/db/update.py:159`) launches these workers via
`multiprocessing.Pool(processes=cpu_count())`.

If the start method ever changes (platform default differs, or a future
change calls `multiprocessing.set_start_method("spawn")`), every warning
call in a worker raises `RuntimeError: Working outside of application
context`, and since that call *is* the exception handler for the general
failure case (`projection.py:36-39`), the error is unguarded and propagates
out of `pool.imap_unordered`, aborting the entire heap's projection pass.

Currently dormant (works fine on Linux/fork today), but fragile — a Python
version bump, a container base image change, or portability work (e.g.
running on macOS in dev, where `spawn` has been the default since Python
3.8) could silently break every projection run.

## 2. Design choices

- **Fix approach.** Options considered: (a) pass a plain
  `logging.getLogger(...)` into worker processes instead of touching
  `current_app`; (b) initialize a minimal Flask app context explicitly in a
  `Pool` initializer function (`initializer=` arg), so `current_app` keeps
  working as-is inside workers. **Chosen: (a)** — workers only ever log, they
  don't need any other app-context-derived state (config, `g`, etc.), so a
  standalone module-level logger is simpler and removes the fork dependency
  entirely rather than papering over it with a context that has to be
  re-pushed per worker.

## 3. Approach

- `backend/app/db/projection.py`: replace
  `current_app.logger.warning(...)` calls in `process_player()` with a
  module-level `logger = logging.getLogger("app.db.projection")`, matching
  the pattern already used in `staging.py`/`update.py`. Remove the `flask`
  import if nothing else in the file needs it.
- No change needed to `update.py::project_players()` — the `Pool` call
  itself doesn't touch Flask state.

**Files involved:**
- `backend/app/db/projection.py` (modified)
