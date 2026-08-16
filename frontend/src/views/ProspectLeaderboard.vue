<script setup>
import { ref, watch, onMounted } from 'vue'
import { ArrowUpCircleIcon } from '@heroicons/vue/20/solid'

// Same lookup + per-file duplication convention as ProspectPipeline.vue
// (ticket 0070/0073) -- not shared across files.
const LEVEL_LABELS = {
  1: 'MLB',
  2: 'AAA',
  3: 'AA',
  4: 'A / High-A',
  6: 'Rookie / Complex',
  0: "Int'l Complex",
}
const LEVEL_ORDER = [1, 2, 3, 4, 6, 0]
const POSITION_ORDER = ['C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF', 'DH', 'P']

const loading = ref(true)
const error = ref(null)
const topOverall = ref({ page: 1, page_size: 20, total: 0, results: [] })
const topByPosition = ref({})
const topByLevel = ref({})

const positionFilter = ref('')
const levelFilter = ref('')
const page = ref(1)
const pageSize = 20

async function fetchLeaderboard() {
  loading.value = true
  error.value = null
  try {
    const params = new URLSearchParams({
      leaderboard: '1',
      page: String(page.value),
      page_size: String(pageSize),
    })
    if (positionFilter.value) params.set('position', positionFilter.value)
    // levelFilter !== '' (not a truthy check): level 0 ("Int'l Complex",
    // ticket 0073) is a real, selectable filter value that's otherwise
    // falsy and indistinguishable from the "All Levels" default -- same
    // gotcha ProspectPipeline.vue's level filter already hit.
    if (levelFilter.value !== '') params.set('level', levelFilter.value)

    const res = await fetch(`/api/prospects?${params}`)
    if (!res.ok) throw new Error('Failed to load leaderboard.')
    const data = await res.json()
    topOverall.value = data.top_overall
    topByPosition.value = data.top_by_position
    topByLevel.value = data.top_by_level
  } catch (err) {
    error.value = err.message || 'Failed to load leaderboard.'
  } finally {
    loading.value = false
  }
}

onMounted(fetchLeaderboard)

// Filter changes reset to page 1 -- otherwise a filter that shrinks the
// result set could leave the user stranded on a now-nonexistent page.
watch([positionFilter, levelFilter], () => {
  page.value = 1
  fetchLeaderboard()
})
watch(page, fetchLeaderboard)

function goToPage(delta) {
  const next = page.value + delta
  if (next < 1) return
  if ((next - 1) * pageSize >= topOverall.value.total && delta > 0) return
  page.value = next
}

// Whole-dollar figures are unreadable unformatted at this scale -- same
// compact-currency convention as SurplusValue.vue/ProspectPipeline.vue.
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

// Same tiering as ProspectPipeline.vue (ticket 0070/0072) -- no "bad" tier,
// even a low-ceiling prospect is a real asset, not a liability.
function fvClass(fv) {
  if (fv >= 55) return 'bg-team-subtle text-team'
  if (fv >= 45) return 'bg-gray-100 text-gray-800'
  return 'bg-amber-50 text-amber-900'
}

function riskTagTitle(riskTag) {
  if (riskTag === '-') return 'Higher risk: still far from his talent ceiling'
  if (riskTag === '+') return 'Lower risk: already close to his talent ceiling'
  return undefined
}

function orderedPositionEntries(byPosition) {
  return POSITION_ORDER.filter((pos) => byPosition[pos]?.length).map((pos) => [pos, byPosition[pos]])
}

function orderedLevelEntries(byLevel) {
  return LEVEL_ORDER.filter((lvl) => byLevel[String(lvl)]?.length).map((lvl) => [lvl, byLevel[String(lvl)]])
}

const totalPages = () => Math.max(1, Math.ceil(topOverall.value.total / pageSize))
</script>

<template>
  <div class="max-w-6xl mx-auto p-6">
    <h1 class="text-xl font-bold rounded-lg px-4 py-3 mb-6 bg-team text-team-on-bg">
      League-Wide Prospect Leaderboard
    </h1>

    <div class="flex flex-wrap gap-3 mb-6 text-sm">
      <select v-model="positionFilter" class="border border-gray-300 rounded-md py-1.5 px-3">
        <option value="">All Positions</option>
        <option v-for="pos in POSITION_ORDER" :key="pos" :value="pos">{{ pos }}</option>
      </select>
      <select v-model="levelFilter" class="border border-gray-300 rounded-md py-1.5 px-3">
        <option value="">All Levels</option>
        <option v-for="lvl in LEVEL_ORDER" :key="lvl" :value="lvl">{{ LEVEL_LABELS[lvl] }}</option>
      </select>
    </div>

    <div v-if="loading" class="text-gray-500">Loading...</div>
    <div v-else-if="error" class="text-red-500">{{ error }}</div>
    <div v-else>
      <!-- Top overall (paginated) -->
      <section class="mb-10">
        <h2 class="text-lg font-semibold mb-3">
          Overall ({{ topOverall.total }} prospect{{ topOverall.total === 1 ? '' : 's' }})
        </h2>

        <div v-if="topOverall.results.length === 0" class="text-gray-500 text-sm">
          No prospects match this filter.
        </div>

        <div v-else class="overflow-x-auto">
          <table class="w-full text-sm bg-white rounded-lg shadow-sm border border-gray-200">
            <thead>
              <tr class="bg-gray-100 text-gray-600 text-left">
                <th class="px-3 py-2">Rank</th>
                <th class="px-3 py-2">Player</th>
                <th class="px-3 py-2">Pos</th>
                <th class="px-3 py-2">Age</th>
                <th class="px-3 py-2">Level</th>
                <th class="px-3 py-2">Org</th>
                <th class="px-3 py-2">FV</th>
                <th class="px-3 py-2">Surplus Value</th>
                <th class="px-3 py-2">Star Odds</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(prospect, index) in topOverall.results"
                :key="prospect.player_id"
                class="even:bg-gray-50 border-t border-gray-100"
              >
                <td class="px-3 py-2 text-gray-400">
                  {{ (topOverall.page - 1) * topOverall.page_size + index + 1 }}
                </td>
                <td class="px-3 py-2">
                  <router-link
                    :to="`/players/${prospect.player_id}`"
                    class="hover:underline hover:text-team font-medium"
                  >
                    {{ prospect.first_name }} {{ prospect.last_name }}
                  </router-link>
                  <ArrowUpCircleIcon
                    v-if="prospect.value.mlb_promotion_ready"
                    class="inline-block h-4 w-4 text-team align-text-bottom"
                    title="MLB promotion ready: current-form projection already grades as a bench player/backend starter or better"
                  />
                </td>
                <td class="px-3 py-2">{{ prospect.position }}</td>
                <td class="px-3 py-2">{{ prospect.age }}</td>
                <td class="px-3 py-2">{{ LEVEL_LABELS[prospect.level] || prospect.level }}</td>
                <td class="px-3 py-2 text-gray-400 text-xs whitespace-nowrap">{{ prospect.org_abbr }}</td>
                <td class="px-3 py-2">
                  <span
                    class="px-2 py-0.5 rounded-full text-xs font-semibold"
                    :class="fvClass(prospect.value.fv)"
                    :title="riskTagTitle(prospect.value.risk_tag)"
                  >
                    {{ prospect.value.fv }}<template v-if="prospect.value.risk_tag"> {{ prospect.value.risk_tag }}</template>
                  </span>
                </td>
                <td class="px-3 py-2 font-medium">{{ formatMoney(prospect.value.surplus_value) }}</td>
                <td class="px-3 py-2">{{ formatPercent(prospect.value.star_odds) }}</td>
              </tr>
            </tbody>
          </table>

          <div class="flex items-center justify-between mt-3 text-sm">
            <button
              class="px-3 py-1.5 rounded-md border border-gray-300 disabled:opacity-40"
              :disabled="page <= 1"
              @click="goToPage(-1)"
            >
              Previous
            </button>
            <span class="text-gray-500">Page {{ topOverall.page }} of {{ totalPages() }}</span>
            <button
              class="px-3 py-1.5 rounded-md border border-gray-300 disabled:opacity-40"
              :disabled="page * pageSize >= topOverall.total"
              @click="goToPage(1)"
            >
              Next
            </button>
          </div>
        </div>
      </section>

      <!-- Top by position -->
      <section class="mb-10">
        <h2 class="text-lg font-semibold mb-3">Top 10 by Position</h2>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <div
            v-for="[pos, group] in orderedPositionEntries(topByPosition)"
            :key="pos"
            class="bg-white rounded-lg shadow-sm border border-gray-200 p-4"
          >
            <h3 class="text-sm font-semibold text-team uppercase tracking-wide mb-2 pb-2 border-b border-gray-100">
              {{ pos }}
            </h3>
            <ol class="text-sm space-y-1">
              <li v-for="(prospect, index) in group" :key="prospect.player_id" class="flex items-center gap-2">
                <span class="text-gray-400 w-4 text-right">{{ index + 1 }}</span>
                <router-link :to="`/players/${prospect.player_id}`" class="hover:underline hover:text-team flex-1 truncate">
                  {{ prospect.first_name }} {{ prospect.last_name }}
                </router-link>
                <span class="text-gray-400 text-xs whitespace-nowrap">{{ prospect.org_abbr }}</span>
                <span class="px-1.5 py-0.5 rounded-full text-xs font-semibold" :class="fvClass(prospect.value.fv)">
                  {{ prospect.value.fv }}
                </span>
              </li>
            </ol>
          </div>
        </div>
      </section>

      <!-- Top by level -->
      <section>
        <h2 class="text-lg font-semibold mb-3">Top 10 by Level</h2>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <div
            v-for="[lvl, group] in orderedLevelEntries(topByLevel)"
            :key="lvl"
            class="bg-white rounded-lg shadow-sm border border-gray-200 p-4"
          >
            <h3 class="text-sm font-semibold text-team uppercase tracking-wide mb-2 pb-2 border-b border-gray-100">
              {{ LEVEL_LABELS[lvl] || lvl }}
            </h3>
            <ol class="text-sm space-y-1">
              <li v-for="(prospect, index) in group" :key="prospect.player_id" class="flex items-center gap-2">
                <span class="text-gray-400 w-4 text-right">{{ index + 1 }}</span>
                <router-link :to="`/players/${prospect.player_id}`" class="hover:underline hover:text-team flex-1 truncate">
                  {{ prospect.first_name }} {{ prospect.last_name }}
                </router-link>
                <span class="text-gray-400 text-xs whitespace-nowrap">{{ prospect.org_abbr }}</span>
                <span class="px-1.5 py-0.5 rounded-full text-xs font-semibold" :class="fvClass(prospect.value.fv)">
                  {{ prospect.value.fv }}
                </span>
              </li>
            </ol>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>
