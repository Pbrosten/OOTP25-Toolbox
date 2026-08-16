<script setup>
import { ref, onMounted, computed } from 'vue'
import { TabGroup, TabList, Tab, TabPanels, TabPanel } from '@headlessui/vue'
import { ArrowUpCircleIcon } from '@heroicons/vue/20/solid'

const props = defineProps({
  id: { type: [String, Number], required: true },
})

// level -> label (ticket 0062: 1=MLB, 2=AAA, 3=AA, 4=A/High-A, 6=Rookie/
// Complex -- 5 never appears, it's this save's exhibition-team anomaly).
// Hardcoded here, not stored, per 0062's design choice.
const LEVEL_LABELS = {
  1: 'MLB',
  2: 'AAA',
  3: 'AA',
  4: 'A / High-A',
  6: 'Rookie / Complex',
}
const LEVEL_ORDER = [1, 2, 3, 4, 6]

// Levels far enough from MLB-readiness that current-rating WAR isn't a
// meaningful ranking signal (ticket 0064, see app/api/teams.py) -- the API
// returns a roster count per position instead of a ranked player list.
const COUNT_ONLY_LEVELS = new Set([4, 6])

// Standard defensive-spectrum display order, plus SP/RP for pitchers and
// TWP (two-way players, ticket 0067) last -- players.position = 'P' with
// no recognized pitcher role that heap.
const GROUP_ORDER = ['C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF', 'DH', 'SP', 'RP', 'TWP']
const PITCHER_GROUPS = new Set(['SP', 'RP', 'TWP'])

const loading = ref(true)
const error = ref(null)
const depthChart = ref(null)
const prospects = ref([])

async function fetchDepthChart() {
  loading.value = true
  error.value = null
  try {
    const [depthChartRes, prospectsRes] = await Promise.all([
      fetch(`/api/teams/${props.id}/depth-chart`),
      // Ticket 0078: A/High-A and Rookie/Complex (COUNT_ONLY_LEVELS) get a
      // top-10 prospect ranking below their count tiles, using 0068's
      // talent-ceiling FV calc -- current-rating WAR (what the count-only
      // levels were built around, ticket 0064) isn't a meaningful ranking
      // signal that far from MLB-readiness, but FV specifically is. Reuses
      // the existing org-scoped GET /api/prospects (0069) as-is, no
      // backend changes -- one extra request, sorted/grouped client-side
      // the same way ProspectPipeline.vue already sorts its own fetch.
      fetch(`/api/prospects?team_id=${props.id}`),
    ])
    if (depthChartRes.ok) {
      depthChart.value = await depthChartRes.json()
    } else {
      error.value = 'Team not found.'
    }
    if (prospectsRes.ok) {
      prospects.value = await prospectsRes.json()
    }
  } catch (err) {
    error.value = 'Failed to load depth chart.'
  } finally {
    loading.value = false
  }
}

onMounted(fetchDepthChart)

// Top-10 prospects per count-only level (ticket 0078), ranked by fv desc /
// surplus_value desc as tiebreak -- one combined list per level, not
// broken out by position (per user's explicit choice, distinct from how
// the WAR-ranked levels above are grouped).
const topProspectsByLevel = computed(() => {
  const byLevel = {}
  for (const level of COUNT_ONLY_LEVELS) {
    byLevel[level] = prospects.value
      .filter((p) => p.level === level && p.value.available)
      .sort((a, b) => b.value.fv - a.value.fv || b.value.surplus_value - a.value.surplus_value)
      .slice(0, 10)
  }
  return byLevel
})

const levels = computed(() => {
  if (!depthChart.value) return []
  return LEVEL_ORDER.filter((level) => depthChart.value.levels[String(level)])
})

// Org color theming (ticket 0064): the MLB team's own real colors
// (teams.background_color/text_color), applied to this page only -- an
// app-wide "set my org" theme selector is deliberately out of scope here,
// filed as its own ticket.
const teamColors = computed(() => ({
  '--team-bg': depthChart.value?.background_color || '#0f766e',
  '--team-text': depthChart.value?.text_color || '#ffffff',
}))

function sortedGroups(groups) {
  const keys = Object.keys(groups)
  return keys.sort((a, b) => {
    const ai = GROUP_ORDER.indexOf(a)
    const bi = GROUP_ORDER.indexOf(b)
    if (ai === -1 && bi === -1) return a.localeCompare(b)
    if (ai === -1) return 1
    if (bi === -1) return -1
    return ai - bi
  })
}

// Two-column layout for the WAR-ranked levels (MLB/AAA/AA): position
// players on the left, pitchers (SP/RP) on the right.
function batterGroups(groups) {
  return sortedGroups(groups).filter((g) => !PITCHER_GROUPS.has(g))
}

function pitcherGroups(groups) {
  return sortedGroups(groups).filter((g) => PITCHER_GROUPS.has(g))
}

function formatWar(war) {
  return war === null || war === undefined ? '-' : Number(war).toFixed(1)
}

function warClass(war) {
  if (war === null || war === undefined) return 'text-gray-400'
  return Number(war) >= 0 ? 'text-teal-700' : 'text-red-600'
}

// FV badge tiering (ticket 0078) -- same convention as ProspectPipeline.vue
// (0070/0072): no "bad" tier, even a low-ceiling prospect is a real asset.
function fvClass(fv) {
  if (fv >= 55) return 'bg-teal-50 text-teal-900'
  if (fv >= 45) return 'bg-gray-100 text-gray-800'
  return 'bg-amber-50 text-amber-900'
}

function riskTagTitle(riskTag) {
  if (riskTag === '-') return 'Higher risk: still far from his talent ceiling'
  if (riskTag === '+') return 'Lower risk: already close to his talent ceiling'
  return undefined
}
</script>

<template>
  <div class="max-w-6xl mx-auto p-6" :style="teamColors">
    <div v-if="loading" class="text-gray-500">Loading...</div>
    <div v-else-if="error" class="text-red-500">{{ error }}</div>
    <div v-else-if="depthChart">
      <h1
        class="text-xl font-bold rounded-lg px-4 py-3 mb-6"
        style="background-color: var(--team-bg); color: var(--team-text);"
      >
        {{ depthChart.team_name }}
      </h1>

      <TabGroup>
        <TabList class="flex gap-1 border-b border-gray-200 mb-6">
          <Tab v-for="level in levels" :key="level" v-slot="{ selected }" as="template">
            <button
              class="px-4 py-2 text-sm font-semibold rounded-t-md focus:outline-none transition-colors"
              :style="selected ? { backgroundColor: 'var(--team-bg)', color: 'var(--team-text)' } : {}"
              :class="!selected && 'text-gray-600 hover:bg-gray-100'"
            >
              {{ LEVEL_LABELS[level] }}
            </button>
          </Tab>
        </TabList>

        <TabPanels>
          <TabPanel v-for="level in levels" :key="level">
            <!-- A/Rookie (levels 4, 6): roster counts only, no WAR ranking
                 (ticket 0064 -- current-rating WAR isn't meaningful that
                 far from MLB-readiness). A top-10 prospect ranking (ticket
                 0078) is added below, using 0068's talent-ceiling FV calc
                 instead -- the signal 0064 was missing at the time. -->
            <template v-if="COUNT_ONLY_LEVELS.has(level)">
              <div class="flex flex-wrap gap-3">
                <div
                  v-for="group in sortedGroups(depthChart.levels[String(level)])"
                  :key="group"
                  class="bg-white rounded-lg shadow-sm border border-gray-200 px-4 py-3 min-w-[90px] text-center"
                >
                  <div class="text-xs font-semibold text-gray-500 uppercase tracking-wide">{{ group }}</div>
                  <div class="text-2xl font-bold text-gray-800">{{ depthChart.levels[String(level)][group] }}</div>
                </div>
              </div>

              <div class="mt-6">
                <h2 class="text-xs font-bold text-gray-400 uppercase tracking-wide mb-3">Top 10 Prospects</h2>
                <div v-if="topProspectsByLevel[level]?.length === 0" class="text-gray-500 text-sm">
                  No ranked prospects at this level.
                </div>
                <table v-else class="w-full max-w-2xl text-sm bg-white rounded-lg shadow-sm border border-gray-200">
                  <tbody>
                    <tr
                      v-for="(prospect, index) in topProspectsByLevel[level]"
                      :key="prospect.player_id"
                      class="even:bg-gray-50 border-t border-gray-100 first:border-t-0"
                    >
                      <td class="px-3 py-2 text-gray-400 w-6">{{ index + 1 }}</td>
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
                      <td class="px-3 py-2 text-gray-400 text-xs whitespace-nowrap">{{ prospect.position }}</td>
                      <td class="px-3 py-2">
                        <span
                          class="px-2 py-0.5 rounded-full text-xs font-semibold"
                          :class="fvClass(prospect.value.fv)"
                          :title="riskTagTitle(prospect.value.risk_tag)"
                        >
                          {{ prospect.value.fv }}<template v-if="prospect.value.risk_tag"> {{ prospect.value.risk_tag }}</template>
                        </span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </template>

            <!-- MLB/AAA/AA (levels 1, 2, 3): WAR-ranked player lists, two
                 columns -- position players on the left, pitchers (SP/RP)
                 on the right. -->
            <div v-else class="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
              <div
                v-for="column in [
                  { label: 'Position Players', groups: batterGroups(depthChart.levels[String(level)]) },
                  { label: 'Pitchers', groups: pitcherGroups(depthChart.levels[String(level)]) },
                ]"
                :key="column.label"
              >
                <h2 class="text-xs font-bold text-gray-400 uppercase tracking-wide mb-3">{{ column.label }}</h2>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div
                    v-for="group in column.groups"
                    :key="group"
                    class="bg-white rounded-lg shadow-sm border border-gray-200 p-4"
                  >
                    <h3 class="text-sm font-semibold text-teal-800 uppercase tracking-wide mb-2 pb-2 border-b border-gray-100">
                      {{ group }}
                    </h3>
                    <table class="w-full text-sm">
                      <tbody>
                        <tr
                          v-for="player in depthChart.levels[String(level)][group]"
                          :key="player.player_id"
                          class="even:bg-gray-50"
                        >
                          <td class="py-1 pr-2">
                            <router-link
                              :to="`/players/${player.player_id}`"
                              class="hover:underline hover:text-teal-800"
                            >
                              {{ player.first_name }} {{ player.last_name }}
                            </router-link>
                            <ArrowUpCircleIcon
                              v-if="player.is_promotion_candidate"
                              class="inline-block h-4 w-4 text-teal-600 align-text-bottom"
                              title="Promotion candidate: top 20% of WAR at this level, league-wide"
                            />
                          </td>
                          <td class="py-1 pr-2 text-gray-400 text-xs whitespace-nowrap">{{ player.team_abbr }}</td>
                          <td class="py-1 text-right font-medium whitespace-nowrap" :class="warClass(player.war)">
                            {{ formatWar(player.war) }}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>
          </TabPanel>
        </TabPanels>
      </TabGroup>
    </div>
  </div>
</template>
