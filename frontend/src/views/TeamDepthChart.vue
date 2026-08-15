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

async function fetchDepthChart() {
  loading.value = true
  error.value = null
  try {
    const response = await fetch(`/api/teams/${props.id}/depth-chart`)
    if (response.ok) {
      depthChart.value = await response.json()
    } else {
      error.value = 'Team not found.'
    }
  } catch (err) {
    error.value = 'Failed to load depth chart.'
  } finally {
    loading.value = false
  }
}

onMounted(fetchDepthChart)

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
                 far from MLB-readiness). -->
            <div v-if="COUNT_ONLY_LEVELS.has(level)" class="flex flex-wrap gap-3">
              <div
                v-for="group in sortedGroups(depthChart.levels[String(level)])"
                :key="group"
                class="bg-white rounded-lg shadow-sm border border-gray-200 px-4 py-3 min-w-[90px] text-center"
              >
                <div class="text-xs font-semibold text-gray-500 uppercase tracking-wide">{{ group }}</div>
                <div class="text-2xl font-bold text-gray-800">{{ depthChart.levels[String(level)][group] }}</div>
              </div>
            </div>

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
