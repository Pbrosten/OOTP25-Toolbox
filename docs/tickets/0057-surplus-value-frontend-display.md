# 0057 — Surplus-value frontend display

- **Tag:** feat
- **Status:** Open
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
- **"Not available" is a normal state, not an error.** Two-way players, free
  agents with no contract on file, and players with no current-heap WAR all
  return `{"available": false}` from 0056's route (200, not 4xx). Render an
  explicit "Surplus value not available for this player" message, same
  treatment `DevelopmentTrends` gives "not enough history yet".

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

Manual verification: run the dev stack (`podman compose up`), open a player
with a real contract in the `TEST.lg` save, confirm the numbers roughly
match what 0056's throwaway-DB spot-check produced; check a two-way and a
no-contract player render the "not available" state cleanly.

**Files involved:**
- `frontend/src/components/SurplusValue.vue` (new)
- `frontend/src/components/PlayerDetails.vue` (modified — mount the new
  component)
