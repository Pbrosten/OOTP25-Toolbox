<script setup lang='ts'>
import { ref, onMounted, computed, watch } from 'vue'
import {
  Switch,
  Listbox,
  ListboxLabel,
  ListboxButton,
  ListboxOptions,
  ListboxOption,
} from '@headlessui/vue'
import { CheckIcon, ChevronUpDownIcon } from '@heroicons/vue/20/solid'
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
  batting_runs_percentile: "Batting Run Value",
  basepath_runs_percentile: "Basepath Run Value",
  fielding_runs_percentile: "Fielding Run Value",
  total_runs_percentile: "Total Run Value",
}

const valueOrder = [
  'batting_runs_percentile',
  'fielding_runs_percentile',
  'basepath_runs_percentile',
  'total_runs_percentile',
]

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
const xStatsValue = ref<any>(null)
const xStatsBat = ref<any>(null)
const xStatsRun = ref<any>(null)
const xStatsField = ref<any>(null)

const loading = ref(true)
const error = ref<string | null>(null)

const mlbComp = ref<boolean>(leagueId == 203)
const mlbLock = computed(() => leagueId === 203)

const years = ref<any>(null)
const selectedYear = ref(null)

onMounted(() => {
  fetchPercentiles()
  getYears()
})

watch(mlbComp, () => {
  fetchPercentiles()
})

watch(selectedYear, async (newYear) => {
  if (newYear) {
    await fetchPercentiles(newYear.rating_id)
  }
})


function sortedEntries(obj: any, order: string[]) {
  return order
    .map(key => [key, obj[key]])
    .filter(([_, value]) => isValidPercentile(value))
}

function getStatLabel(key: string): string {
  return statLabelMap[key] || key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

// Raw value shown next to the bar (Savant-style) -- only for genuine
// projected statistics, not raw game ratings/grades that borrow
// outcome-stat names (Barrel %, Bat Speed, Chase %, Whiff %, Sprint Speed,
// Stealing Value, Extra Bases, Arm Value, Range Value, Framing all stay
// percentile-bar-only). Explicit map rather than mechanical
// key.replace('_percentile', '_value') like PitcherPercentiles.vue uses,
// since fielding_value_percentile's raw value is already named
// fielding_value (no doubled "_value" suffix) in
// get_player_expected_fielding_percentiles.sql.
const VALUE_KEY_MAP: Record<string, string> = {
  batting_runs_percentile: 'batting_runs_value',
  basepath_runs_percentile: 'basepath_runs_value',
  fielding_runs_percentile: 'fielding_runs_value',
  total_runs_percentile: 'total_runs_value',
  xba_percentile: 'xba_value',
  xslg_percentile: 'xslg_value',
  xwoba_percentile: 'xwoba_value',
  fielding_value_percentile: 'fielding_value',
}

const RATE_VALUE_KEYS = new Set(['xba_percentile', 'xslg_percentile', 'xwoba_percentile'])

function getStatValue(source: any, key: string): string | undefined {
  const valueKey = VALUE_KEY_MAP[key]
  if (!valueKey) return undefined
  const raw = source?.[valueKey]
  if (raw === null || raw === undefined) return undefined
  const num = Number(raw)
  if (RATE_VALUE_KEYS.has(key)) return num.toFixed(3).replace(/^0\./, '.')
  return num.toFixed(1)
}

function formatYear(dateString: string): string {
  const date = new Date(dateString)
  return date.getFullYear().toString()
}

async function getYears() {
  if (!years.value) {
    const yearsRes = await fetch(`/api/players/${props.playerId}/ratings?years=true`)
    console.log(yearsRes)
    if (yearsRes.ok) {
      years.value = await yearsRes.json()
      console.log(years.value)
      selectedYear.value = years.value[0]
    } else {
      throw new Error(`Failed to load player rating years.`)
    }
  }
}

async function fetchPercentiles(ratingId?: number) {
  loading.value = true
  error.value = null

  try {
    if (!ratingId) {
      const ratingRes = await fetch(`/api/players/${props.playerId}/ratings?latest=true`)
      if (ratingRes.ok) {
        const ratingData = await ratingRes.json()
        ratingId = ratingData.rating_id
      } else {
        throw new Error('Failed to load player rating info.')
      }
    }

    const valueRes = await fetch(`/api/players/ratings/${ratingId}/expected/value/percentiles?mlb=${mlbComp.value}`)
    xStatsValue.value = valueRes.ok ? await valueRes.json() : null
    if (!valueRes.ok) throw new Error('Failed to load expected value stats.')

    const batRes = await fetch(`/api/players/ratings/${ratingId}/expected/batting/percentiles?mlb=${mlbComp.value}`)
    xStatsBat.value = batRes.ok ? await batRes.json() : null
    if (!batRes.ok) throw new Error('Failed to load expected batting stats.')

    const runRes = await fetch(`/api/players/ratings/${ratingId}/expected/basepath/percentiles?mlb=${mlbComp.value}`)
    xStatsRun.value = runRes.ok ? await runRes.json() : null
    if (!runRes.ok) throw new Error('Failed to load expected basepath stats.')

    const fieldRes = await fetch(`/api/players/ratings/${ratingId}/expected/fielding/percentiles?mlb=${mlbComp.value}`)
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
        <span v-if="leagueId !== 203" class="text-sm font-medium text-gray-700">Current</span>
        <Switch v-model="mlbComp" :class="[
          'relative inline-flex h-6 w-11 items-center rounded-full',
          mlbComp ? 'bg-teal-800' : 'bg-gray-200',
          mlbLock ? 'cursor-not-allowed opacity-60' : ''
        ]" :disabled="mlbLock">
          <span :class="[
            'inline-block h-4 w-4 transform rounded-full bg-white transition',
            mlbComp ? 'translate-x-6' : 'translate-x-1'
          ]" />
        </Switch>
        <span class="text-sm font-medium text-gray-700">MLB</span>
        <Listbox v-model="selectedYear">
          <div class="relative mt-1">
            <ListboxButton
              class="min-w-[5rem] w-auto cursor-default rounded-lg bg-white py-2 pl-3 pr-10 text-left shadow-md focus:outline-none focus-visible:border-indigo-500 focus-visible:ring-2 focus-visible:ring-white/75 focus-visible:ring-offset-2 focus-visible:ring-offset-teal-600 sm:text-sm">
              <span class="block truncate">{{ formatYear(selectedYear.rating_date) }}</span>
              <span class="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
                <ChevronUpDownIcon class="h-5 w-5 text-gray-400" aria-hidden="true" />
              </span>
            </ListboxButton>

            <transition leave-active-class="transition duration-100 ease-in" leave-from-class="opacity-100"
              leave-to-class="opacity-0">
              <ListboxOptions
                class="absolute z-10 mt-1 w-[6rem] max-h-60 overflow-auto rounded-md bg-white py-1 text-base shadow-lg ring-1 ring-black/5 focus:outline-none sm:text-sm">

                <ListboxOption v-slot="{ active, selected }" v-for="year in years" :key="year.rating_date" :value="year"
                  as="template">
                  <li :class="[
                    active ? 'bg-teal-100 text-teal-900' : 'text-gray-900',
                    'relative cursor-default select-none py-2 pl-10 pr-4',
                  ]">
                    <span :class="[
                      selected ? 'font-medium' : 'font-normal',
                      'block truncate',
                    ]">{{ formatYear(year.rating_date) }}</span>
                    <span v-if="selected" class="absolute inset-y-0 left-0 flex items-center pl-3 text-amber-600">
                      <CheckIcon class="h-5 w-5" aria-hidden="true" />
                    </span>
                  </li>
                </ListboxOption>
              </ListboxOptions>
            </transition>
          </div>
        </Listbox>
      </div>
      <div v-if='xStatsBat'>
        <div class="relative w-full h-10">
          <div class="absolute inset-x-0 bottom-1.25 h-0.5 bg-teal-600"></div>

          <div class="relative flex items-center space-x-2 h-full px-4">
            <img src="@/assets/slider-trophy.png" class="w-10 h-10" />
            <h3 class="text-base font-semibold">Value</h3>
          </div>
        </div>
        <div class="grid grid-cols-[150px_1fr_44px] items-end gap-3 mb-1">
          <div></div>
          <div class="flex justify-between text-[10px] font-semibold text-gray-400 uppercase tracking-wide leading-tight">
            <span class="flex flex-col items-start"><span>Poor</span><span>&#9650;</span></span>
            <span class="flex flex-col items-center"><span>Average</span><span>&#9650;</span></span>
            <span class="flex flex-col items-end"><span>Great</span><span>&#9650;</span></span>
          </div>
          <div></div>
        </div>
        <template v-for="[key, value] in sortedEntries(xStatsValue, valueOrder)" :key="key">
          <PercentileBar :label="getStatLabel(key)" :percentile="Number(value)" :value="getStatValue(xStatsValue, key)" />
        </template>
      </div>

      <div v-if='xStatsBat'>
        <div class="relative w-full h-10">
          <div class="absolute inset-x-0 bottom-1.25 h-0.5 bg-teal-600"></div>

          <div class="relative flex items-center space-x-2 h-full px-4">
            <img src="@/assets/slider-batter.png" class="w-10 h-10" />
            <h3 class="text-base font-semibold">Batting</h3>
          </div>
        </div>
        <div class="grid grid-cols-[150px_1fr_44px] items-end gap-3 mb-1">
          <div></div>
          <div class="flex justify-between text-[10px] font-semibold text-gray-400 uppercase tracking-wide leading-tight">
            <span class="flex flex-col items-start"><span>Poor</span><span>&#9650;</span></span>
            <span class="flex flex-col items-center"><span>Average</span><span>&#9650;</span></span>
            <span class="flex flex-col items-end"><span>Great</span><span>&#9650;</span></span>
          </div>
          <div></div>
        </div>
        <template v-for="[key, value] in sortedEntries(xStatsBat, battingOrder)" :key="key">
          <PercentileBar :label="getStatLabel(key)" :percentile="Number(value)" :value="getStatValue(xStatsBat, key)" />
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
        <div class="grid grid-cols-[150px_1fr_44px] items-end gap-3 mb-1">
          <div></div>
          <div class="flex justify-between text-[10px] font-semibold text-gray-400 uppercase tracking-wide leading-tight">
            <span class="flex flex-col items-start"><span>Poor</span><span>&#9650;</span></span>
            <span class="flex flex-col items-center"><span>Average</span><span>&#9650;</span></span>
            <span class="flex flex-col items-end"><span>Great</span><span>&#9650;</span></span>
          </div>
          <div></div>
        </div>
        <template v-for="[key, value] in sortedEntries(filteredFieldingPercentiles, fieldOrder)" :key="key">
          <PercentileBar :label="getStatLabel(key)" :percentile="Number(value)" :value="getStatValue(xStatsField, key)" />
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
        <div class="grid grid-cols-[150px_1fr_44px] items-end gap-3 mb-1">
          <div></div>
          <div class="flex justify-between text-[10px] font-semibold text-gray-400 uppercase tracking-wide leading-tight">
            <span class="flex flex-col items-start"><span>Poor</span><span>&#9650;</span></span>
            <span class="flex flex-col items-center"><span>Average</span><span>&#9650;</span></span>
            <span class="flex flex-col items-end"><span>Great</span><span>&#9650;</span></span>
          </div>
          <div></div>
        </div>
        <template v-for="[key, value] in sortedEntries(xStatsRun, basepathOrder)" :key="key">
          <PercentileBar :label="getStatLabel(key)" :percentile="Number(value)" :value="getStatValue(xStatsRun, key)" />
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