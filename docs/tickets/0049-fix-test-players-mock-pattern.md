# 0049 — Fix broken DB-connection mocks in `tests/api/test_players.py`

- **Tag:** chore
- **Status:** Open
- **Depends on:** —
- **Blocks:** —

## 1. Problem

All 11 tests in `backend/tests/api/test_players.py` fail — confirmed
pre-existing and unrelated to any in-flight work (`git stash`/`git stash
pop` around an unrelated change reproduced the identical 11 failures with
or without that change; the rest of the suite is unaffected — `75 passed`
elsewhere in the same run).

Every test in the file mocks the DB connection the same wrong way:

```python
mock_con = MagicMock()
mock_cursor = MagicMock()
mock_cursor.fetchall.return_value = [...]
mock_con.execute.return_value = mock_cursor   # <- wrong call, wrong shape
mock_get_db.return_value = mock_con
```

But every real route in `app/api/players.py` calls `con.cursor()` as a
context manager, not `con.execute()` directly:

```python
with con.cursor() as cursor:
    cursor.execute(...)
    rows = cursor.fetchall()
```

Since `mock_con` is an unconfigured `MagicMock`, `mock_con.cursor()` auto-
generates its own child mock, and `with ... as cursor` on that returns yet
another unconfigured mock via `__enter__` — never the `mock_cursor` the
test carefully set up. The real route ends up calling `.fetchall()`/
`.fetchone()` on a mock that returns a fresh `MagicMock`, which then fails
to JSON-serialize (`TypeError: Object of type MagicMock is not JSON
serializable`) or simply returns wrong/empty data, depending on the route.

Two of the eleven (`test_get_player_career_batting_mlb`,
`test_get_player_career_batting_not_found`) compound this with a second
issue: they set `mock_con.execute.side_effect = [check_cursor,
stats_cursor]`, modeling two separate cursor objects — but the real
`get_player_career_batting` route opens **one** `cursor` via a single `with
con.cursor() as cursor:` block and calls `cursor.execute()` on it twice
(once for the MLB-stats existence check, once for the actual data),
reading `.fetchone()` then `.fetchall()` off that same cursor. The test's
two-cursor structure doesn't match the implementation's shape at all.

`tests/db/test_update.py` already has the correct pattern for this same
"code under test uses `with con.cursor() as cursor:`" shape:
`db.cursor.return_value.__enter__.return_value = mock_cursor` — this
should be mirrored here, not reinvented.

## 2. Design choices

- **Fix in place, don't rewrite from scratch.** Each test's assertions and
  intent are still valid (right status codes, right response shapes) — only
  the mock wiring is wrong. This is narrower than
  [0017](0017-rewrite-stale-pipeline-tests.md)'s "rewrite or remove" scope,
  which dealt with tests validating behavior that had actually changed;
  here the tests were seemingly never correctly wired in the first place.
- **Outstanding:** while investigating, found `get_player_career_pitching`
  (`app/api/players.py`) — a real, existing route — has **zero** test
  coverage in this file (no `test_get_player_career_pitching_*` at all,
  unlike its batting counterpart which has two). Whether to add that
  coverage as part of this cleanup or leave it for a separate ticket isn't
  decided here.

## 3. Approach

- For the 9 single-query tests (`test_get_players`,
  `test_get_player_by_id_found`, `test_get_player_by_id_not_found`,
  `test_search_players`, `test_get_player_details_by_id_found`,
  `test_get_player_details_by_id_not_found`, `test_get_player_ratings_all`,
  `test_get_player_ratings_latest`, `test_get_player_ratings_not_found`):
  replace `mock_con.execute.return_value = mock_cursor` with
  `mock_con.cursor.return_value.__enter__.return_value = mock_cursor`,
  matching `tests/db/test_update.py`'s existing pattern.
- For the 2 two-query tests (`test_get_player_career_batting_mlb`,
  `test_get_player_career_batting_not_found`): use a single `mock_cursor`
  wired the same way, with `mock_cursor.fetchone.return_value` (the
  MLB-stats check) and `mock_cursor.fetchall.return_value` (the actual
  data) set directly — `cursor.execute()` itself doesn't need a
  `side_effect`, since the real code never reads its return value.
- Re-run `pytest tests/api/test_players.py` to confirm all 11 pass, then
  the full suite to confirm no regressions elsewhere.

**Files involved:**
- `backend/tests/api/test_players.py` (modified)
