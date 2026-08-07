# 0008 — Derive is_production from env; stop printing config with secrets

- **Tag:** fix
- **Status:** Closed
- **Depends on:** —
- **Blocks:** —

## 1. Problem

`backend/app/__init__.py:10` hardcodes `is_production = False` as a literal,
so `config.ProdConfig` is unreachable dead code — every deployment runs with
`DEBUG=True`, `TESTING=True` regardless of environment, unless someone edits
this source line. Separately, `backend/app/__init__.py:17` unconditionally
runs `print(app.config)`, which dumps the entire Flask config — including
`DB_PASSWORD` and `ADMIN_API_TOKEN` in plaintext (both loaded in
`backend/config.py:14,16`) — to stdout/container logs on every process
start.

Debug mode in a real deployment exposes the Werkzeug debugger (arbitrary
code execution via the interactive traceback) and verbose error pages. The
config print leaks the admin token and DB password into container logs,
which are typically retained/aggregated longer and more broadly readable
than the `.env` file itself.

## 2. Design choices

- **Environment source.** Options considered: (a) a dedicated `APP_ENV`
  env var (e.g. `APP_ENV=production`); (b) reuse Flask's built-in
  `FLASK_ENV`/`FLASK_DEBUG`. **Chosen: (a)**, a dedicated `APP_ENV` read in
  `create_app()` — `FLASK_ENV` was deprecated by Flask itself and
  `FLASK_DEBUG` conflates "debug mode" with "which config class," which are
  two different concerns here (a prod deployment might still want `DEBUG`
  toggled independently for troubleshooting).
- **Config print.** Delete `print(app.config)` outright rather than
  redacting it — no current operational need for a startup config dump was
  identified, and a redaction allowlist is one more thing to keep in sync as
  config keys are added.

## 3. Approach

- `backend/config.py`: no change to the config classes themselves.
- `backend/app/__init__.py`: replace the hardcoded `is_production = False`
  with `is_production = os.environ.get("APP_ENV") == "production"`; remove
  the `print(app.config)` line entirely.
- `backend/templates/.env-template`: document `APP_ENV` (default unset /
  `development`; set to `production` in prod deployments).
- Update `docker-compose.yml` / any deployment docs that reference env vars
  if `APP_ENV` needs to be set there for a "real" deployment target (this
  repo currently only documents local dev via `podman compose up`, so this
  may be a no-op beyond the template).

**Files involved:**
- `backend/app/__init__.py` (modified)
- `backend/templates/.env-template` (modified)
