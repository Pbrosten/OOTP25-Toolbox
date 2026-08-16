<script setup lang="ts">
import { ref, onMounted } from 'vue'

const props = defineProps<{ playerId: number }>()

interface SurplusYear {
  year_offset: number
  age: number
  war: number
  value: number
  cost: number
  surplus: number
}

// Two disconnected valuation methodologies live behind this one component
// (ticket 0071): 0056's contract-based surplus value (requires a signed
// contract) and 0068's FV-based prospect value (talent-ceiling projection,
// no contract needed). A prospect almost never has a real contract, so
// 0056's route came back {"available": false} for essentially every
// prospect while the farm-system list showed a real number for the same
// player -- this component now checks GET /api/prospects/{id} first and
// switches its whole display mode based on whether the player currently
// qualifies as a prospect (0043's definition), rather than trying to
// force both methodologies into one shape.
const mode = ref<'contract' | 'prospect'>('contract')

// --- contract-based (ticket 0056/0057/0058) ---
const available = ref(false)
const recommendation = ref<string | null>(null)
const totalValue = ref(0)
const totalCost = ref(0)
const totalSurplus = ref(0)
const years = ref<SurplusYear[]>([])

// --- FV-based prospect value (ticket 0068/0071) ---
const prospectAvailable = ref(false)
const fv = ref(0)
const expectedSurplusValue = ref(0)
const expectedWar = ref(0)
const starOdds = ref(0)
const mlbPromotionReady = ref<boolean | null>(null)

const loading = ref(true)
const error = ref<string | null>(null)

onMounted(fetchValue)

async function fetchValue() {
  loading.value = true
  error.value = null

  try {
    const prospectRes = await fetch(`/api/prospects/${props.playerId}`)
    if (!prospectRes.ok) throw new Error('Failed to load prospect value.')
    const prospectData = await prospectRes.json()

    if (prospectData.is_prospect) {
      mode.value = 'prospect'
      prospectAvailable.value = prospectData.available
      if (prospectData.available) {
        fv.value = prospectData.fv
        expectedSurplusValue.value = prospectData.surplus_value
        expectedWar.value = prospectData.expected_war
        starOdds.value = prospectData.star_odds
        mlbPromotionReady.value = prospectData.mlb_promotion_ready ?? null
      }
      return
    }

    mode.value = 'contract'
    const res = await fetch(`/api/players/${props.playerId}/surplus-value`)
    if (!res.ok) throw new Error('Failed to load surplus value.')
    const data = await res.json()
    available.value = data.available
    if (data.available) {
      recommendation.value = data.recommendation
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

// Ticket 0058's decision table groups into three real outcomes for a GM
// glancing at this badge: "good news" (worth keeping/extending), "neutral/
// exit" (let it play out or move him), "cut him loose now" (non-tender) --
// colored accordingly rather than a five-way palette.
const recommendationClass: Record<string, string> = {
  Extend: 'bg-teal-50 text-teal-900',
  'Keep short-term': 'bg-teal-50 text-teal-900',
  'Trade before free agency': 'bg-amber-50 text-amber-900',
  'Let walk': 'bg-amber-50 text-amber-900',
  'Non-tender': 'bg-red-50 text-red-900',
}

// No "bad" tier for a prospect's FV grade (unlike the recommendation
// colors above) -- even a low-ceiling prospect is a real asset, not a
// liability. Same tiering as ProspectPipeline.vue (ticket 0070).
function fvClass(grade: number): string {
  if (grade >= 55) return 'bg-teal-50 text-teal-900'
  if (grade >= 45) return 'bg-gray-100 text-gray-800'
  return 'bg-amber-50 text-amber-900'
}

// Whole-dollar figures at this scale (six-to-nine digits) are unreadable
// unformatted -- compact notation ("$8.3M") matches how the underlying
// $/WAR constant itself is discussed in ticket 0056.
function formatMoney(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(value)
}

function formatWar(value: number): string {
  return value.toFixed(1)
}

function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`
}
</script>

<template>
  <div class="surplus-value-wrapper w-full">
    <div v-if="loading" class="text-gray-500 text-sm">Loading...</div>
    <div v-else-if="error" class="text-red-500 text-sm">{{ error }}</div>

    <!-- FV-based prospect value (ticket 0068/0071) -->
    <template v-else-if="mode === 'prospect'">
      <h2 class="text-lg font-semibold mb-2">Prospect Value</h2>
      <div v-if="!prospectAvailable" class="text-gray-500 text-sm">
        Prospect value not available for this player.
      </div>
      <template v-else>
        <p class="text-xs text-gray-500 mb-3">
          Probabilistic farm-system valuation from this player's talent ceiling, not a
          year-by-year contract projection.
        </p>
        <span
          v-if="mlbPromotionReady"
          class="inline-block px-3 py-1 mb-3 rounded-full text-sm font-semibold bg-teal-50 text-teal-900"
        >
          MLB Promotion Ready
        </span>
        <div class="flex gap-4 text-sm">
          <div
            class="flex-none w-16 h-16 rounded flex flex-col items-center justify-center"
            :class="fvClass(fv)"
          >
            <div class="text-xs opacity-70">FV</div>
            <div class="font-semibold text-lg">{{ fv }}</div>
          </div>
          <div class="flex-1 px-3 py-2 rounded bg-gray-50 text-center">
            <div class="text-gray-500">Expected Surplus Value</div>
            <div class="font-semibold">{{ formatMoney(expectedSurplusValue) }}</div>
          </div>
          <div class="flex-1 px-3 py-2 rounded bg-gray-50 text-center">
            <div class="text-gray-500">Expected WAR</div>
            <div class="font-semibold">{{ formatWar(expectedWar) }}</div>
          </div>
          <div class="flex-1 px-3 py-2 rounded bg-gray-50 text-center">
            <div class="text-gray-500">Star Odds</div>
            <div class="font-semibold">{{ formatPercent(starOdds) }}</div>
          </div>
        </div>
      </template>
    </template>

    <!-- Contract-based surplus value (ticket 0056/0057/0058) -->
    <template v-else>
      <h2 class="text-lg font-semibold mb-2">Surplus Value</h2>
      <!-- Two-way players, unsigned free agents, and players with no
           current-heap WAR all come back {"available": false} from 0056's
           route -- a normal state, not an error (ticket 0057's Design
           choices). -->
      <div v-if="!available" class="text-gray-500 text-sm">
        Surplus value not available for this player.
      </div>

      <template v-else>
        <div
          v-if="recommendation"
          class="inline-block px-3 py-1 mb-3 rounded-full text-sm font-semibold"
          :class="recommendationClass[recommendation] || 'bg-gray-50 text-gray-900'"
        >
          {{ recommendation }}
        </div>

        <div class="flex flex-wrap gap-4 mb-4 text-sm">
          <div class="px-3 py-2 rounded bg-gray-50">
            <div class="text-gray-500">Projected Value</div>
            <div class="font-semibold">{{ formatMoney(totalValue) }}</div>
          </div>
          <div class="px-3 py-2 rounded bg-gray-50">
            <div class="text-gray-500">Projected Cost</div>
            <div class="font-semibold">{{ formatMoney(totalCost) }}</div>
          </div>
          <div
            class="px-3 py-2 rounded"
            :class="totalSurplus >= 0 ? 'bg-teal-50 text-teal-900' : 'bg-red-50 text-red-900'"
          >
            <div>Surplus</div>
            <div class="font-semibold">{{ formatMoney(totalSurplus) }}</div>
          </div>
        </div>

        <div class="overflow-x-auto max-h-64 overflow-y-auto">
          <table class="w-full max-w-2xl table-auto border-collapse text-sm">
            <thead>
              <tr class="bg-gray-200 text-gray-700">
                <th class="px-2 py-1">Age</th>
                <th class="px-2 py-1">WAR</th>
                <th class="px-2 py-1">Value</th>
                <th class="px-2 py-1">Cost</th>
                <th class="px-2 py-1">Surplus</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="yr in years" :key="yr.year_offset" class="even:bg-gray-50">
                <td class="px-2 py-1">{{ yr.age }}</td>
                <td class="px-2 py-1">{{ formatWar(yr.war) }}</td>
                <td class="px-2 py-1">{{ formatMoney(yr.value) }}</td>
                <td class="px-2 py-1">{{ formatMoney(yr.cost) }}</td>
                <td
                  class="px-2 py-1"
                  :class="yr.surplus >= 0 ? 'text-teal-700' : 'text-red-600'"
                >
                  {{ formatMoney(yr.surplus) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </template>
  </div>
</template>

<style scoped>
.surplus-value-wrapper {
  width: 100%;
}
</style>
