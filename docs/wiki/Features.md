# Features

[← Back to Home](Home.md)

The frontend (`http://localhost:5173`) has these views.

## Player Search — `/search`

A type-ahead search box. As you type, it queries
`GET /api/players/search?q=<query>` (matched against player first+last name)
and lists up to 10 matches with position and team. Selecting a result, or
pressing Enter with a single match, navigates to that player's profile.

## Player Profile — `/players/:id`

The main analytics view for a single player. It shows:

- **Player details** — bio/ratings info pulled from `/api/players/:id/details`.
- **Batter percentiles** (for non-pitchers) — a percentile-profile comparison
  of the player's expected offense/defense/basepath/run-value against a
  cohort of their position and league, backed by the
  `/api/players/ratings/*/expected/*/percentiles` endpoints. This is what
  answers "how good is this player's projected performance *relative to
  their peers*," not just in absolute terms.
- **Pitcher percentiles** (`position === 'P'`) — the pitching equivalent,
  comparing expected production (ERA, xBA/xwOBA against, ratings) and
  run-value/WAR against a cohort of pitchers in the same league, backed by
  `/api/players/ratings/*/expected/pitching/percentiles`
  ([0027](../tickets/0027-pitcher-api-frontend-wiring.md)).

## Admin Panel — `/admin`

A trigger UI for the [Admin API](Admin-API.md), for when you'd rather click a
button than `curl`:

- **Initialize Database** — calls `init-db` synchronously (confirms first,
  since it's destructive) and shows the result inline.
- **Update Database** — calls `update-db`, then polls the returned job every
  2 seconds and shows a pending/running/succeeded/failed status plus the
  final result or error. If a job is already running (`409`), it picks up
  polling that job instead of erroring.

Not linked from the landing page nav (there isn't a shared nav component
yet) — reachable directly by URL. The first admin action in a browser tab
prompts for the `X-Admin-Token` (see [Admin API → Authentication](Admin-API.md#authentication))
and caches it in `sessionStorage` for the rest of that tab's session.

> Only shows job `status`/`result`/`error`, not a live log of what's
> happening during the run — that's tracked separately in
> [docs/tickets/0006-job-log-capture.md](../tickets/0006-job-log-capture.md).

## Underlying data: projections & run value

The percentile views are computed from data produced during
[`update-db`](Updating-the-Database.md): each monthly heap's ratings are run
through the batter projection system to produce expected stats
(`*_expected` tables) and an estimated run value (`players_run_value`). The
UI doesn't compute these live — it reads the results of the last database
update, so a profile only reflects data as current as your last
`update-db` run. For how the ratings-to-stats math actually works, see
[Projections](Projections.md).

## API reference

For the full set of read endpoints backing these views (ratings, batting,
fielding, basepath, career stats, etc.), see
[`backend/docs/openai.yaml`](../../backend/docs/openai.yaml) — it's kept in
sync with the actual routes under `backend/app/api/`.
