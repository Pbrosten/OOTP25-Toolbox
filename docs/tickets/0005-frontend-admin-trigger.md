# 0005 — Frontend trigger for admin DB operations

- **Tag:** feat
- **Status:** Closed
- **Depends on:** [0004](0004-async-update-db-job.md)
- **Blocks:** —

## 1. Problem

The original motivation for 0002–0004 was to let `init-db`/`update-db` be
triggered "from the UI or a CLI curl request." The API side covers the curl case;
there's still no frontend affordance to trigger these operations or watch
`update-db` job progress.

## 2. Design choices

- **Where it lives.** Options considered: a dedicated admin route, or a panel
  bolted onto an existing page (e.g. the landing page). **Chosen: dedicated
  route** (`/admin`, `AdminPanel.vue`) — keeps destructive controls separate
  from the analytics views and gives the token gate (below) one clear place
  to live, rather than sprinkling admin-only UI into `LandingPage.vue`.
- **Progress detail.** Options considered: a simple status indicator polling
  job `status`, or a live per-line log tail. A log tail needs the backend to
  capture log lines per job, which [0004](0004-async-update-db-job.md)'s job
  record (`status`/`result`/`error` only) doesn't do. **Chosen: simple status
  indicator** for this ticket — poll `GET /api/admin/jobs/{job_id}` and show
  pending/running/succeeded/failed plus the final `result`/`error`. Log tail
  is split out to [0006](0006-job-log-capture.md) as backend + frontend
  follow-up work, so this ticket isn't blocked on undesigned backend changes.
- **Admin token handling.** Options considered: (a) bake a token into the
  frontend build via a Vite env var, (b) prompt for it at runtime and hold it
  in memory only, (c) prompt at runtime and persist it in `sessionStorage`.
  (a) was rejected — it ships the shared secret inside the compiled JS bundle,
  which is the "committing a shared secret to frontend source" case flagged as
  unacceptable. **Chosen: (c)** runtime prompt + `sessionStorage`: the first
  admin action prompts for the token if none is stored, uses it for that and
  subsequent requests, and clears when the tab closes. Never touches the
  frontend build or git history; re-entering per browser session is an
  acceptable trade-off for how rarely this page will be used.
- **Outstanding:** `sessionStorage` is readable by any script on the page
  (XSS exposure), acceptable for the same reason 0003 accepted a static env
  var — this is a trusted internal tool with no other auth surface today.
  Revisit if this is ever exposed beyond a trusted network.

## 3. Approach

- Add `frontend/src/api/admin.ts`: thin fetch wrapper for
  `POST /api/admin/init-db`, `POST /api/admin/update-db`, and
  `GET /api/admin/jobs/{job_id}`, attaching the `X-Admin-Token` header from a
  small token-store helper (`frontend/src/api/adminToken.ts`) that reads from
  `sessionStorage`, prompting (`window.prompt`) and persisting on first use if
  absent.
- Add `frontend/src/views/AdminPanel.vue`:
  - "Initialize Database" button → calls `init-db`, shows the result or error
    inline. Confirms before firing, since it's destructive.
  - "Update Database" button → calls `update-db`, then polls
    `GET /jobs/{job_id}` on an interval until `succeeded`/`failed`, showing a
    spinner + status text and the final result/error. Disabled while a job
    from this session is in flight, and surfaces the `409` "already in
    progress" case if another caller started one.
- Register the route in `frontend/src/router/index.ts` (`/admin` →
  `AdminPanel.vue`). No nav-bar link added in this ticket (no shared nav
  component exists yet) — reachable by URL, matching the "internal tool,
  minimal surface" posture of 0003.

**Files involved:**
- `frontend/src/api/admin.ts` (new)
- `frontend/src/api/adminToken.ts` (new)
- `frontend/src/views/AdminPanel.vue` (new)
- `frontend/src/router/index.ts` (modified)
