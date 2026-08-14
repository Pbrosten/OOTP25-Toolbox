# 0055 — Fix semicolon inside a comment breaking `migration_short.sql`

- **Tag:** fix
- **Status:** Closed
- **Depends on:** —
- **Blocks:** —

## 1. Problem

Real `flask --app app update-db` run failed while processing a short (monthly)
heap:

```
[ERROR] Migration failed: (1064, "You have an error in your SQL syntax; check
the manual that corresponds to your MariaDB server version for the right
syntax to use near 'confirmed against a real dump export: position=1/Pitcher
-- pairs with role 1...' at line 1")
```

`app/db/update.py`'s `_run_sql_script` splits each migration file into
statements with a naive `sql_script.strip().split(";")` — it has no notion
of `-- ...` comments or string literals, so *any* semicolon anywhere in the
file, including inside a comment, is treated as a statement boundary.

`migration_short.sql` line 15 (added by
[0030](0030-exclude-pitchers-from-batting-projection.md), commit `ccf7544`)
reads:

```sql
-- non-pitcher; confirmed against a real dump export: position=1/Pitcher
```

The `;` after "non-pitcher" splits the script there. Everything from that
point up to the *next* real semicolon — several more comment lines followed
by the actual `INSERT INTO players_batting ...` statement — becomes one
"statement" that starts with raw prose ("confirmed against a real dump
export: position=1/Pitcher"), which MariaDB correctly rejects as invalid
SQL.

This bug has existed since 0030 shipped; it wasn't caught because ticket
[0053](0053-contract-service-time-schema.md)/[0054](0054-contract-service-time-migration.md)'s
verification only exercised the long/yearly heap in isolation (a scratch
`DUMP_PATH` containing just `dump_2025_yearly`), never a short heap.

## 2. Design choices

- **Fix the offending comment vs. harden the splitter.** Two options: (a)
  remove the semicolon from this one comment — a one-line, zero-risk fix
  that unblocks real `update-db` runs immediately; (b) replace the naive
  `.split(";")` in `_run_sql_script` with something that understands SQL
  comments/string literals (e.g. `sqlparse`, or a regex that strips `--`
  comments before splitting), which would prevent every *future* instance
  of this same class of bug, not just this one. **Chosen: (a) for this
  ticket** — it's the blocking issue, small, and safe. **Outstanding:** (b)
  is a real latent fragility (any future migration-script comment
  containing a semicolon reintroduces this exact failure mode with no
  compile-time or test-time warning) but is a broader behavior change to
  shared migration-execution code, out of scope for a same-day unblock fix.
  Not decided whether to pursue it — flagging for a separate ticket if
  wanted.

## 3. Approach

- `migration_short.sql`: reworded the comment on line 15 to avoid the
  semicolon (`;` → `--`, matching the file's existing style for joining
  comment clauses elsewhere in the same block).
- Verified on a throwaway MariaDB container (not the persistent
  `mariadb_data` volume), against the real `TEST.lg` save:
  - `dump_2025_01` (short) + `dump_2025_yearly` (long) together: both
    processed without error (short heap ran against an empty `players`
    table per the documented ordering limitation — 0 ratings inserted,
    expected).
  - `dump_2025_02` (short) processed afterward, with `players` now
    populated: 186,543 ratings inserted, 46,910 projections generated, no
    errors — confirms the previously-unreachable `players_batting` insert
    (the one after the fixed comment) actually executes correctly, not
    just that the script parses.
  - Backend test suite: 86 passed.

**Files involved:**
- `backend/app/db/sql_scripts/migration/migration_short.sql` (modified)
