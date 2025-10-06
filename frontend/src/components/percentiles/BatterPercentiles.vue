<script setup lang='ts'>
import { ref, onMounted, computed, watch } from 'vue'
import { Switch } from '@headlessui/vue'
import PercentileBar from './PercentileBar.vue'

const props = defineProps<{ playerId: number, leagueId: number | null }>()
const leagueId = props.leagueId ?? 203
const positionGroupFields = {
  catcher: [
    'catcher_arm_percentile',
    'catcher_framing_percentile',
    'fielding_value_percentile',
  ],
  infield: [
    'infield_arm_percentile',
    'infield_range_percentile',
    'fielding_value_percentile',
  ],
  outfield: [
    'outfield_arm_percentile',
    'outfield_range_percentile',
    'fielding_value_percentile',
  ],
}

const statLabelMap: Record<string, string> = {
  xwoba_percentile: 'xwOBA',
  xba_percentile: 'xBA',
  xslg_percentile: 'xSLG',
  xbabip_percentile: 'xBABIP',
  barrel_rate: 'Barrel %',
  swing_speed: 'Bat Speed',
  chase_rate: 'Chase %',
  whiff_rate: 'Whiff %',
  sprint_speed: 'Sprint Speed',
  steal_value: 'Stealing Value',
  extra_base_taken: 'Extra Bases',
  fielding_value_percentile: 'Fielding Value',
  catcher_arm_percentile: 'Arm Value',
  catcher_framing_percentile: 'Framing',
  infield_arm_percentile: 'Arm Value',
  infield_range_percentile: 'Range Value',
  outfield_arm_percentile: 'Arm Value',
  outfield_range_percentile: 'Range Value',

}

const battingOrder = [
  'xwoba_percentile',
  'xba_percentile',
  'xslg_percentile',
  'xbabip_percentile',
  'barrel_rate',
  'swing_speed',
  'chase_rate',
  'whiff_rate',
]
const basepathOrder = [
  'sprint_speed',
  'steal_value',
  'extra_base_taken',
]
const fieldOrder = [
  'catcher_framing_percentile',
  'infield_range_percentile',
  'outfield_range_percentile',
  'catcher_arm_percentile',
  'infield_arm_percentile',
  'outfield_arm_percentile',
]

const playerRating = ref<any>(null)
const xStatsBat = ref<any>(null)
const xStatsRun = ref<any>(null)
const xStatsField = ref<any>(null)

const loading = ref(true)
const error = ref<string | null>(null)

const mlbComp = ref<boolean>(leagueId==203)
const mlbLock = computed(() => leagueId === 203)

onMounted(() => {
  fetchPercentiles()
})

watch(mlbComp, () => {
  fetchPercentiles()
})

function sortedEntries(obj: any, order: string[]) {
  return order
    .map(key => [key, obj[key]])
    .filter(([_, value]) => isValidPercentile(value))
}

function getStatLabel(key: string): string {
  return statLabelMap[key] || key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

async function fetchPercentiles() {
  loading.value = true
  error.value = null

  try {
    // Fetch latest rating ID if not loaded
    if (!playerRating.value) {
      const ratingRes = await fetch(`/api/players/${props.playerId}/ratings?latest=true`)
      if (ratingRes.ok) {
        playerRating.value = await ratingRes.json()
      } else {
        throw new Error('Failed to load player rating info.')
      }
    }

    const ratingId = playerRating.value.rating_id

    // Fetch Batting Stats
    const batRes = await fetch(`/api/players/stats/expected/batting/${ratingId}/percentiles?mlb=${mlbComp.value}`)
    xStatsBat.value = batRes.ok ? await batRes.json() : null
    if (!batRes.ok) throw new Error('Failed to load expected batting stats.')

    // Fetch Basepath Stats
    const runRes = await fetch(`/api/players/stats/expected/basepath/${ratingId}/percentiles?mlb=${mlbComp.value}`)
    xStatsRun.value = runRes.ok ? await runRes.json() : null
    if (!runRes.ok) throw new Error('Failed to load expected basepath stats.')

    // Fetch Fielding Stats
    const fieldRes = await fetch(`/api/players/stats/expected/fielding/${ratingId}/percentiles?mlb=${mlbComp.value}`)
    xStatsField.value = fieldRes.ok ? await fieldRes.json() : null
    if (!fieldRes.ok) throw new Error('Failed to load expected fielding stats.')

  } catch (err: any) {
    error.value = err.message || 'An error occurred.'
  } finally {
    loading.value = false
  }
}


// Helper: Check if value is a valid percentile (0–100)
function isValidPercentile(value: any): boolean {
  const num = Number(value)
  return !isNaN(num) && num >= 0 && num <= 100
}

const filteredFieldingPercentiles = computed(() => {
  if (!xStatsField.value) return {}

  const group = xStatsField.value.position_group?.toLowerCase()

  if (!group || !(group in positionGroupFields)) {
    // fallback: just show keys ending with _percentile with valid values
    return Object.fromEntries(
      Object.entries(xStatsField.value).filter(
        ([key, value]) => key.endsWith('_percentile') && isValidPercentile(value)
      )
    )
  }

  // filter keys based on position group relevance and valid percentile
  return Object.fromEntries(
    Object.entries(xStatsField.value).filter(
      ([key, value]) =>
        positionGroupFields[group].includes(key) && isValidPercentile(value)
    )
  )
})
</script>

<template>
  <div class="percentiles-wrapper">
    <div v-if='loading'>Loading...</div>
    <div v-else-if='error'>{{ error }}</div>
    <div v-else>
      <div class="flex items-center space-x-4">
        <h2 class="text-lg font-semibold">Percentiles</h2>
        <Switch
          v-model="mlbComp"
          :class="[
            'relative inline-flex h-6 w-11 items-center rounded-full',
            mlbComp ? 'bg-teal-800' : 'bg-gray-200',
            mlbLock ? 'cursor-not-allowed opacity-60' : ''
          ]"
          :disabled="mlbLock"
        >
          <span
            :class="[
              'inline-block h-4 w-4 transform rounded-full bg-white transition',
              mlbComp ? 'translate-x-6' : 'translate-x-1'
            ]"
          />
        </Switch>
        <span class="text-sm font-medium text-gray-700">Compare to MLB</span>
      </div>
      <div v-if='xStatsBat'>
        <div class="relative w-full h-10">
          <div class="absolute inset-x-0 bottom-1.25 h-0.5 bg-teal-600"></div>

          <div class="relative flex items-center space-x-2 h-full px-4">
            <img src="@/assets/slider-batter.png" class="w-10 h-10" />
            <h3 class="text-base font-semibold">Batting</h3>
          </div>
        </div>
        <template v-for="[key, value] in sortedEntries(xStatsBat, battingOrder)" :key="key">
          <PercentileBar :label="getStatLabel(key)" :percentile="Number(value)" />
        </template>
      </div>

      <div v-if='filteredFieldingPercentiles'>
        <div class="relative w-full h-10">
          <div class="absolute inset-x-0 bottom-1.25 h-0.5 bg-teal-600"></div>

          <div class="relative flex items-center space-x-2 h-full px-4">
            <img src="@/assets/slider-fielder.png" class="w-10 h-10" />
            <h3 class="text-base font-semibold">Fielding</h3>
          </div>
        </div>
        <template v-for="[key, value] in sortedEntries(filteredFieldingPercentiles, fieldOrder)" :key="key">
          <PercentileBar :label="getStatLabel(key)" :percentile="Number(value)" />
        </template>
      </div>

      <div v-if='xStatsRun'>
        <div class="relative w-full h-10">
          <div class="absolute inset-x-0 bottom-1.25 h-0.5 bg-teal-600"></div>

          <div class="relative flex items-center space-x-2 h-full px-4">
            <img src="@/assets/slider-runner.png" class="w-10 h-10" />
            <h3 class="text-base font-semibold">Base Running</h3>
          </div>
        </div>
        <template v-for="[key, value] in sortedEntries(xStatsRun, basepathOrder)" :key="key">
          <PercentileBar :label="getStatLabel(key)" :percentile="Number(value)" />
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.percentiles-wrapper {
  width: 100%;
}
</style>