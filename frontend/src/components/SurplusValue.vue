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

const available = ref(false)
const totalValue = ref(0)
const totalCost = ref(0)
const totalSurplus = ref(0)
const years = ref<SurplusYear[]>([])
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
</script>

<template>
  <div class="surplus-value-wrapper w-full">
    <h2 class="text-lg font-semibold mb-2">Surplus Value</h2>
    <div v-if="loading" class="text-gray-500 text-sm">Loading...</div>
    <div v-else-if="error" class="text-red-500 text-sm">{{ error }}</div>

    <template v-else>
      <!-- Two-way players, unsigned free agents, and players with no
           current-heap WAR all come back {"available": false} from 0056's
           route -- a normal state, not an error (ticket 0057's Design
           choices). -->
      <div v-if="!available" class="text-gray-500 text-sm">
        Surplus value not available for this player.
      </div>

      <template v-else>
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
