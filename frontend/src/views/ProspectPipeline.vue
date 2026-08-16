<script setup>
import { ref, onMounted, computed } from 'vue'
import { ArrowUpCircleIcon, ArrowTrendingUpIcon, ArrowTrendingDownIcon } from '@heroicons/vue/20/solid'

const props = defineProps({
  id: { type: [String, Number], required: true },
})

// level -> label (ticket 0062: 1=MLB, 2=AAA, 3=AA, 4=A/High-A, 6=Rookie/
// Complex -- 5 never appears). Duplicated from TeamDepthChart.vue rather
// than shared -- same per-file convention that component already
// established for this exact lookup.
const LEVEL_LABELS = {
  1: 'MLB',
  2: 'AAA',
  3: 'AA',
  4: 'A / High-A',
  6: 'Rookie / Complex',
}

const POSITION_ORDER = ['C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF', 'DH', 'P']

const loading = ref(true)
const error = ref(null)
const prospects = ref([])
const teamName = ref('')

const levelFilter = ref('')
const positionFilter = ref('')
const sortBy = ref('fv') // 'fv' | 'surplus_value'

async function fetchProspects() {
  loading.value = true
  error.value = null
  try {
    const [prospectsRes, teamsRes] = await Promise.all([
      fetch(`/api/prospects?team_id=${props.id}`),
      fetch('/api/teams'),
    ])
    if (!prospectsRes.ok) throw new Error('Failed to load prospects.')
    prospects.value = await prospectsRes.json()

    if (teamsRes.ok) {
      const teams = await teamsRes.json()
      const team = teams.find((t) => String(t.team_id) === String(props.id))
      teamName.value = team ? `${team.name} ${team.nickname}` : ''
    }
  } catch (err) {
    error.value = err.message || 'Failed to load prospects.'
  } finally {
    loading.value = false
  }
}

onMounted(fetchProspects)

const levels = computed(() => {
  const present = new Set(prospects.value.map((p) => p.level))
  return [1, 2, 3, 4, 6].filter((lvl) => present.has(lvl))
})

const positions = computed(() => {
  const present = new Set(prospects.value.map((p) => p.position))
  return POSITION_ORDER.filter((pos) => present.has(pos))
})

const filteredProspects = computed(() => {
  let rows = prospects.value
  if (levelFilter.value) rows = rows.filter((p) => String(p.level) === String(levelFilter.value))
  if (positionFilter.value) rows = rows.filter((p) => p.position === positionFilter.value)

  // Prospects with no available FV/value (RP-role, or missing rating data
  // -- ticket 0068/0069) always sort last, regardless of sort mode -- same
  // "unavailable sorts last, not first/erroring" convention as
  // TeamDepthChart.vue's null-WAR handling (ticket 0064).
  return [...rows].sort((a, b) => {
    const aVal = a.value.available ? a.value[sortBy.value] : null
    const bVal = b.value.available ? b.value[sortBy.value] : null
    if (aVal === null && bVal === null) return 0
    if (aVal === null) return 1
    if (bVal === null) return -1
    return bVal - aVal
  })
})

// Whole-dollar figures are unreadable unformatted at this scale -- same
// compact-currency convention as SurplusValue.vue (ticket 0057).
function formatMoney(value) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(value)
}

function formatPercent(value) {
  return `${Number(value).toFixed(1)}%`
}

// No "bad" tier for prospects (unlike SurplusValue.vue's recommendation
// colors) -- even a replacement-level-ceiling prospect is still a real
// asset, not a liability. Teal = potential impact player, gray = average
// regular ceiling, amber = organizational depth.
function fvClass(fv) {
  if (fv >= 55) return 'bg-teal-50 text-teal-900'
  if (fv >= 45) return 'bg-gray-100 text-gray-800'
  return 'bg-amber-50 text-amber-900'
}
</script>

<template>
  <div class="max-w-6xl mx-auto p-6">
    <div v-if="loading" class="text-gray-500">Loading...</div>
    <div v-else-if="error" class="text-red-500">{{ error }}</div>
    <div v-else>
      <h1 class="text-xl font-bold rounded-lg px-4 py-3 mb-6 bg-teal-700 text-white">
        {{ teamName || `Org ${id}` }} — Prospect Pipeline
      </h1>

      <div class="flex flex-wrap gap-3 mb-4 text-sm">
        <select v-model="levelFilter" class="border border-gray-300 rounded-md py-1.5 px-3">
          <option value="">All Levels</option>
          <option v-for="lvl in levels" :key="lvl" :value="lvl">{{ LEVEL_LABELS[lvl] }}</option>
        </select>
        <select v-model="positionFilter" class="border border-gray-300 rounded-md py-1.5 px-3">
          <option value="">All Positions</option>
          <option v-for="pos in positions" :key="pos" :value="pos">{{ pos }}</option>
        </select>
        <select v-model="sortBy" class="border border-gray-300 rounded-md py-1.5 px-3">
          <option value="fv">Sort by Future Value</option>
          <option value="surplus_value">Sort by Surplus Value</option>
        </select>
      </div>

      <div v-if="filteredProspects.length === 0" class="text-gray-500 text-sm">
        No prospects match this filter.
      </div>

      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm bg-white rounded-lg shadow-sm border border-gray-200">
          <thead>
            <tr class="bg-gray-100 text-gray-600 text-left">
              <th class="px-3 py-2">Player</th>
              <th class="px-3 py-2">Pos</th>
              <th class="px-3 py-2">Age</th>
              <th class="px-3 py-2">Level</th>
              <th class="px-3 py-2">Team</th>
              <th class="px-3 py-2">FV</th>
              <th class="px-3 py-2">Surplus Value</th>
              <th class="px-3 py-2">Star Odds</th>
              <th class="px-3 py-2">Trend</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="prospect in filteredProspects"
              :key="prospect.player_id"
              class="even:bg-gray-50 border-t border-gray-100"
            >
              <td class="px-3 py-2">
                <router-link
                  :to="`/players/${prospect.player_id}`"
                  class="hover:underline hover:text-teal-800 font-medium"
                >
                  {{ prospect.first_name }} {{ prospect.last_name }}
                </router-link>
                <ArrowUpCircleIcon
                  v-if="prospect.value.mlb_promotion_ready"
                  class="inline-block h-4 w-4 text-teal-600 align-text-bottom"
                  title="MLB promotion ready: current-form projection already grades as a bench player/backend starter or better"
                />
              </td>
              <td class="px-3 py-2">{{ prospect.position }}</td>
              <td class="px-3 py-2">{{ prospect.age }}</td>
              <td class="px-3 py-2">{{ LEVEL_LABELS[prospect.level] || prospect.level }}</td>
              <td class="px-3 py-2 text-gray-400 text-xs whitespace-nowrap">{{ prospect.team_abbr }}</td>

              <template v-if="prospect.value.available">
                <td class="px-3 py-2">
                  <span class="px-2 py-0.5 rounded-full text-xs font-semibold" :class="fvClass(prospect.value.fv)">
                    {{ prospect.value.fv }}
                  </span>
                </td>
                <td class="px-3 py-2 font-medium">{{ formatMoney(prospect.value.surplus_value) }}</td>
                <td class="px-3 py-2">{{ formatPercent(prospect.value.star_odds) }}</td>
              </template>
              <template v-else>
                <td class="px-3 py-2 text-gray-400" colspan="3">Not available</td>
              </template>

              <td class="px-3 py-2">
                <span
                  v-if="prospect.trend.direction === 'up'"
                  class="inline-flex items-center gap-1 text-teal-700"
                  :title="prospect.trend.alerts.map((a) => a.message).join(' ')"
                >
                  <ArrowTrendingUpIcon class="h-4 w-4" /> Improving
                </span>
                <span
                  v-else-if="prospect.trend.direction === 'down'"
                  class="inline-flex items-center gap-1 text-red-600"
                  :title="prospect.trend.alerts.map((a) => a.message).join(' ')"
                >
                  <ArrowTrendingDownIcon class="h-4 w-4" /> Declining
                </span>
                <span
                  v-else-if="prospect.trend.direction === 'mixed'"
                  class="text-amber-700"
                  :title="prospect.trend.alerts.map((a) => a.message).join(' ')"
                >
                  Mixed
                </span>
                <span v-else class="text-gray-300">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
