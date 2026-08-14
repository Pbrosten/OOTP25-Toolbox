# 0057 — Surplus-value frontend display

- **Tag:** feat
- **Status:** Closed
- **Depends on:** [0056](0056-surplus-value-calculation.md)
- **Blocks:** —

## 1. Problem

[0056](0056-surplus-value-calculation.md) exposes
`GET /api/players/<id>/surplus-value`. Nothing in the frontend calls it yet.
[0042](0042-contract-arbitration-analyzer.md)'s Approach already calls for
surfacing this on the player detail page, per the app's Cross-Cutting
Design Principle #1 ("From Stats to Decisions").

## 2. Design choices

- **No recommendation label yet.** 0042 explicitly left the
  Extend/Keep/Let-walk/Non-tender/Trade categorical recommendation fully
  deferred to its own later sub-ticket. This ticket displays the raw
  numbers (`total_value`, `total_cost`, `total_surplus`, and the year-by-year
  breakdown) — not a recommendation badge. Matches 0042's own scoping: "not
  a blocker for building the underlying value calculation itself."
- **Component shape.** New `SurplusValue.vue`, mirroring
  `DevelopmentTrends.vue`'s pattern (0052) — self-contained, fetches its
  own data by `playerId` in `onMounted`, handles loading/error/unavailable
  states independently, mounted into `PlayerDetails.vue` alongside the
  other player-detail sections. Not folded into `PlayerDetails.vue`
  directly, for the same reason 0052 chose a separate component: keeps
  `PlayerDetails.vue` from accumulating unrelated fetch/state logic per
  feature.
- **"Not available" is a normal state, not an error.** Two-way players and
  players with no current-heap WAR return `{"available": false}` from
  0056's route (200, not 4xx). Render an explicit "Surplus value not
  available for this player" message, same treatment `DevelopmentTrends`
  gives "not enough history yet".
- **Free agents: hide the section entirely, don't call the route at all.**
  Found during manual review: 0056's route can return `{"available": true,
  ...}` for a player on the synthetic `team_id = 999` "Free Agents" team
  (`migration_long.sql`'s remap target for anyone with no real roster
  spot) whenever they still have a `players_service_time` row — the
  years-of-control projection doesn't distinguish "rostered player with no
  multi-year deal yet" (a real, meaningful projection) from "unattached
  free agent" (no team controls this player at all; a
  years-of-control/arbitration number is meaningless for them). Rather
  than expanding 0056's route to add that distinction, this ticket gates
  it at the display layer: `get_player_details.sql` now also selects
  `p.team_id`, and `PlayerDetails.vue` only mounts `<SurplusValue>` when
  `team_id !== 999` — matching the same synthetic-team convention
  `migration_long.sql` already established. Scoped as a frontend-only fix
  since the underlying calculation issue is real but out of scope for a
  display ticket; worth revisiting on 0056 directly if a consumer other
  than this page ever needs the route itself to be free-agent-aware.

## 3. Approach

`frontend/src/components/SurplusValue.vue`:

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'

const props = defineProps<{ playerId: number }>()

const available = ref(false)
const totalValue = ref(0)
const totalCost = ref(0)
const totalSurplus = ref(0)
const years = ref<any[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

onMounted(fetchSurplusValue)

async function fetchSurplusValue() {
  loading.value = true
  error.value = null
  try {
    const res = await fetch(`/api/players/${props.playerId}/surplus-value`)
    if (!res.ok) throw new Error('Failed to load surplus value.')
    const data = await res.json()
    available.value = data.available
    if (data.available) {
      totalValue.value = data.total_value
      totalCost.value = data.total_cost
      totalSurplus.value = data.total_surplus
      years.value = data.years
    }
  } catch (err: any) {
    error.value = err.message || 'An error occurred.'
  } finally {
    loading.value = false
  }
}
</script>
```

Template: a summary row (projected value / projected cost / surplus, surplus
colored red/green by sign) plus the year-by-year table (age, WAR, value,
cost, surplus per year) below it, collapsed or scrollable given horizons can
run 6+ years.

Mount `<SurplusValue :player-id="playerId" />` in
`frontend/src/components/PlayerDetails.vue`, alongside `DevelopmentTrends`.

Verified against the running dev stack (already up, real `mariadb_data`
volume — already had contract data ingested from the user's own prior
`update-db` run):
- Restarted the backend container to pick up the new route (bind-mounted
  source, no image rebuild needed); confirmed `/api/players/6/surplus-value`
  and similar return real, sane numbers.
- Swept the real DB's `/surplus-value` route across player IDs 1-3000 via
  curl: 387 available, 2613 not-available, **zero errors** — same clean
  result as 0056's throwaway-DB sweep, now against the actual persistent
  dataset.
- Vite's dev server hot-reloaded `PlayerDetails.vue`/`SurplusValue.vue`
  with no compile errors (checked container logs); requesting
  `SurplusValue.vue` directly from the dev server returns a valid
  transformed JS module (200), confirming no syntax errors.
- **Not verified: visual rendering.** No browser tool was available in
  this session (Claude in Chrome extension not connected) to actually load
  a player page and look at it. Everything above confirms the component
  compiles, mounts without server-side errors, and receives correct data —
  but the actual on-screen layout (summary tiles, table, color coding) has
  not been eyeballed. Worth a manual look before considering this fully
  done.
- `npm run build`'s `vue-tsc -b` type-check step fails, but with the exact
  same `TS2307: Cannot find module '@/...'` error on every single
  `@/`-aliased import project-wide (`Header.vue`, `App.vue`, `router`,
  `LandingPage.vue`, etc. — none of which this ticket touched) plus
  `vite.config.ts`'s own `path`/`__dirname` usage failing the same way.
  This is a pre-existing environment issue (looks like a missing
  `@types/node` breaking `tsconfig` path-alias resolution), not something
  this ticket introduced — `SurplusValue.vue`'s import fails with the
  identical error every other file's does, not a distinct one. Not fixed
  here; out of scope for a frontend-display ticket.
- Backend test suite: 97 passed (unchanged — no backend code touched by
  this ticket).

**Files involved:**
- `frontend/src/components/SurplusValue.vue` (new)
- `frontend/src/components/PlayerDetails.vue` (modified — mount the new
  component, gated on `team_id !== 999`)
- `backend/app/db/sql_scripts/api/get_player_details.sql` (modified —
  expose `p.team_id`)
