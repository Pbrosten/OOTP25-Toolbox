# 0003 — Guard admin endpoints with access control

- **Tag:** feat
- **Status:** Closed
- **Depends on:** [0002](0002-admin-api-endpoints.md)
- **Blocks:** [0004](0004-async-update-db-job.md) (job routes ship behind the same guard)

## 1. Problem

`init-db` drops and recreates the entire schema; `update-db` mutates the database
from dump files. The app currently has **no authentication anywhere** — CORS is
wide open (`CORS(app)` with no restrictions in `app/__init__.py`) and there's no
session/user model. Shipping the routes from 0002 without a guard would let
anyone who can reach the backend port wipe the database with a single `curl`
call.

## 2. Design choices

- **Mechanism.** Options considered:
  - (a) Static shared-secret header (`X-Admin-Token`) checked against an env var —
    simplest, matches the app's current "no auth infra" baseline, no new
    dependencies.
  - (b) IP/network allowlist (e.g. only accept from container network /
    localhost) — fragile once a frontend UI (0005) needs to call it from a
    browser.
  - (c) Full user/session auth — no existing login system to hook into; disproportionate
    for what is currently a single-user local/internal tool.
  - **Chosen: (a)** shared-secret header, as the minimum viable guard given the
    project's current state.
- **Outstanding:** token storage is a single static env var with no rotation
  mechanism. Acceptable for an internal/dev tool today; revisit if this is ever
  exposed beyond a trusted network.
- **Reusability.** Implemented as a decorator (`require_admin_token`) rather than
  inlined per-route, so it can be applied to both routes in 0002 and the job
  routes added in 0004 without duplication.

## 3. Approach

- Add `backend/app/api/auth.py` with a `require_admin_token` decorator:
  - Reads `X-Admin-Token` from the request headers.
  - Compares against `current_app.config["ADMIN_API_TOKEN"]`.
  - Returns `401 {"error": "unauthorized"}` on missing/mismatched token.
- Add `ADMIN_API_TOKEN` to `backend/config.py` (`environ.get("ADMIN_API_TOKEN")`).
- Add `ADMIN_API_TOKEN=` to `backend/templates/.env-template` with a comment
  describing how to generate a value.
- Apply `@require_admin_token` to both routes added in
  [0002](0002-admin-api-endpoints.md).

**Files involved:**
- `backend/app/api/auth.py` (new)
- `backend/app/api/admin.py` (modified — apply decorator)
- `backend/config.py` (modified — new config key)
- `backend/templates/.env-template` (modified — document new var)
