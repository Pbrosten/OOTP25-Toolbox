# Admin API

[← Back to Home](Home.md)

Three routes trigger the database init/update pipeline over HTTP, so it can
be run from a `curl` call or the frontend instead of the CLI. They run
inside the backend container, sidestepping the host/container config
mismatch described in [Configuration](Configuration.md). Full request/response
schemas are also documented in [`backend/docs/openai.yaml`](../../backend/docs/openai.yaml).

All routes are **destructive or long-running** and require the
`X-Admin-Token` header — see [Authentication](#authentication) below.

**UI:** `http://localhost:5173/admin` calls these same routes — see
[Features](Features.md#admin-panel--admin).

## `POST /api/admin/init-db`

(Re)creates the database schema from `schema.sql`. **Destructive** — drops
and recreates tables. Runs synchronously — it's fast (schema DDL only), so
the response is the result itself, not a job to poll.

```bash
curl -X POST http://localhost:5000/api/admin/init-db \
  -H "X-Admin-Token: $ADMIN_API_TOKEN"
```

```json
{ "status": "ok" }
```

## `POST /api/admin/update-db`

Starts ingesting the dump heaps found under `DUMP_PATH` and running the
migration/projection pipeline **as a background job** — mirrors
`flask update-db` exactly (no request parameters), but the request returns
immediately instead of blocking, since a full year of dumps can take tens of
seconds to minutes. Only one update-db job may run at a time.

> Note: despite the name, this currently reprocesses *every* heap under
> `DUMP_PATH` each run, not just new ones — see
> [Ingestion Pipeline](Ingestion-Pipeline.md#3-stage-1--discover-heaps-stagingpycheck_new_heaps).

```bash
curl -X POST http://localhost:5000/api/admin/update-db \
  -H "X-Admin-Token: $ADMIN_API_TOKEN"
```

`202 Accepted`:

```json
{ "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6" }
```

If a job is already `pending`/`running`, the request is rejected instead of
queued:

`409 Conflict`:

```json
{ "error": "update already in progress", "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6" }
```

## `GET /api/admin/jobs/{job_id}`

Poll for the result of a job started via `update-db`.

```bash
curl http://localhost:5000/api/admin/jobs/3fa85f64-5717-4562-b3fc-2c963f66afa6 \
  -H "X-Admin-Token: $ADMIN_API_TOKEN"
```

```json
{
  "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "succeeded",
  "result": {
    "status": "ok",
    "heaps_processed": 2,
    "long_heaps": 1,
    "short_heaps": 1
  },
  "error": null,
  "started_at": "2026-08-06T00:00:00+00:00"
}
```

`status` is one of `pending`, `running`, `succeeded`, or `failed`. `result`
is populated once `succeeded`; `error` is populated once `failed`. A
`job_id` that doesn't exist returns `404 {"error": "job not found"}`.

> Job state lives in memory in the backend process — it doesn't survive a
> restart and isn't shared across multiple workers/replicas. Fine for the
> current single-process dev deployment.

## Authentication

All three routes require an `X-Admin-Token` header matching the
`ADMIN_API_TOKEN` value configured in `backend/.env`:

```bash
X-Admin-Token: <value of ADMIN_API_TOKEN>
```

A missing or mismatched token returns:

```json
{ "error": "unauthorized" }
```

with HTTP status `401`. If `ADMIN_API_TOKEN` isn't set at all, every route
rejects every request (fail closed) rather than allowing unauthenticated
access.

## Error responses

`init-db` returns HTTP `500` on failure (e.g. a bad schema):

```json
{ "error": "<exception message>" }
```

`update-db` failures don't surface as an HTTP error — the job is still
accepted (`202`); the failure shows up as `status: "failed"` with an
`error` message when you poll `GET /api/admin/jobs/{job_id}`.
