# 0051 — Development alert generation (narrative rule layer)

- **Tag:** feat
- **Status:** Open
- **Depends on:** [0050](0050-rating-trend-query-layer.md)
- **Blocks:** [0052](0052-development-monitor-frontend.md)

## 1. Problem

[0044](0044-player-development-monitor.md)'s source doc
(`docs/improvements/expanded-functionality.md` Tier 1 #7) wants narrative
alerts like "contact ability has improved substantially and production has
followed" or "veteran pitcher's stuff and velocity are declining faster than
expected" — not just raw numbers. [0050](0050-rating-trend-query-layer.md)'s
`/trends` route returns per-category deltas and an `exceeded` flag, but no
human-readable text. This ticket turns `exceeded` rows into short alert
strings.

## 2. Design choices

- **Resolved — v1 scope excludes the "production has followed" and
  age-relative clauses.** Per 0044's resolution, actual-vs-projected
  performance correlation and age-curve comparison are both out of scope for
  v1. Alert text in this ticket is limited to the rating-change fact itself
  (direction, category, magnitude) — no claims about whether production
  followed or whether the change is fast/slow for the player's age.
- **Resolved — alert direction wording.** Each in-scope rating column is
  higher-is-better on its own scale (contact, power, stuff, control, speed,
  etc. — there are no lower-is-better raw ratings in the 8 in-scope tables,
  unlike the derived stats in `players_pitching_expected` such as ERA).
  `delta > 0` → "improved", `delta < 0` → "declined". No inversion logic
  needed here (contrast with 0027's ERA/xBA/xwOBA inversion, which was
  needed there because those are derived expected-stats, not raw ratings).
- **Resolved — one alert per exceeded category, not a combined summary.**
  Simpler and composable: the frontend (0052) can group/collapse multiple
  alerts for the same player itself if desired, rather than this layer
  guessing at grouping. Matches the source doc's examples, which read as
  one alert per notable change.
- **Resolved — talent-table alerts use distinct wording from overall-table
  alerts**, since a talent/potential change is scouts revising a ceiling
  estimate, not the player actually getting better or worse right now (e.g.
  "scouts have revised \{player\}'s power potential upward" vs. "\{player\}'s
  power has improved").

## 3. Approach

- New module `backend/app/player_projection/development_alerts.py` (mirrors
  the existing `app/player_projection/batter.py` module boundary — this is
  computation/business logic, not a route handler): a function taking
  0050's trend rows and returning a list of `{player_id, table, column,
  direction, delta, message}` objects, filtered to `exceeded == True`, with
  `message` built from a small per-table wording template (overall vs.
  talent, and a human label per rating column, e.g. `contact` → "contact
  ability", `stuff` → "stuff").
- `backend/app/api/ratings.py`: extend the `/trends` route (or add a sibling
  `GET /api/players/ratings/<int:player_id>/trends/alerts`) to call the new
  module and return only the alert objects — decided as a separate endpoint
  rather than embedding alerts in 0050's response, so 0050's route stays a
  pure data query unaffected by wording changes here.
- `backend/docs/openai.yaml`: document the new route/response shape.

**Files involved:**
- `backend/app/player_projection/development_alerts.py` (new)
- `backend/app/api/ratings.py` (modified)
- `backend/docs/openai.yaml` (modified)
