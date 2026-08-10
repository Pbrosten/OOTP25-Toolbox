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

// Labels follow Baseball Savant's percentile-ranking conventions
// (https://baseballsavant.mlb.com/savant-player/<id>?stats=statcast-r-pitching-mlb).
// xERA/xBA/xwOBA are direct matches (our ERA/BA/wOBA are already
// ratings-derived "expected" stats, not actuals). K %/BB %/Barrel %/
// Hard-Hit %/Fastball Velo/Fastball-Breaking-Offspeed Run Value are
// Savant's real pitch-tracking outcome-stat names borrowed for the closest
// analogous OOTP scouting rating (stuff, control, pbabip, hra, velocity,
// and average players_pitch_repertoire grade per pitch category
// respectively -- see ticket 0034) -- these are still 20-80 (or misc-scale)
// grades under the hood, not derived per-pitch outcome data, but are
// displayed under their outcome-stat names by design, same as the rest of
// this map.
const statLabelMap: Record<string, string> = {
  pitching_runs_percentile: 'Pitching Run Value',
  era_percentile: 'xERA',
  xba_percentile: 'xBA',
  xwoba_percentile: 'xwOBA',
  stuff_percentile: 'K %',
  control_percentile: 'BB %',
  pbabip_percentile: 'Barrel %',
  hra_percentile: 'Hard-Hit %',
  velocity_percentile: 'Fastball Velo',
  fastball_grade_percentile: 'Fastball Run Value',
  breaking_grade_percentile: 'Breaking Run Value',
  offspeed_grade_percentile: 'Offspeed Run Value',
}

// Savant's "Pitch Type Run Value" widget breaks pitching value down into
// Pitching / Fastball / Breaking / Off Speed. 'Pitching Run Value' here is
// the real aggregate run-value figure (players_pitching_run_value.pitching_runs).
// fastball/breaking/offspeed_grade_percentile (ticket 0034) are grouped
// here to match that widget's layout even though they're mechanically a
// rating percentile (combined players_pitch_repertoire grade per category,
// percentiled directly against other pitchers), not derived from
// pitching_runs or any other run-value figure -- see 0034's Design
// choices. baserunning_runs/total_runs/WAR (still returned by the API)
// aren't shown in this section since Savant's run-value widget doesn't mix
// those in either -- it's pitch-based value only.
const valueOrder = [
  'pitching_runs_percentile',
  'fastball_grade_percentile',
  'breaking_grade_percentile',
  'offspeed_grade_percentile',
]

const pitchingOrder = [
  'era_percentile',
  'xba_percentile',
  'xwoba_percentile',
  'velocity_percentile',
  'stuff_percentile',
  'control_percentile',
  'pbabip_percentile',
  'hra_percentile',
]

const xStatsPitch = ref<any>(null)

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

// Only show a raw value for genuine projected statistics (PitcherProjection
// output: expected ERA/xBA/xwOBA, projected run value) -- NOT for raw game
// ratings (stuff/control/pbabip/hra/velocity, and the fastball/breaking/
// offspeed grade percentiles), even though several of those borrow
// outcome-stat names (K %, BB %, ...) per statLabelMap's comment above.
// Showing e.g. a 20-80 `stuff` grade next to a "K %" label would read as a
// real strikeout rate, which it isn't -- so those stay percentile-bar-only,
// no raw number.
const PROJECTED_STAT_KEYS = new Set([
  'pitching_runs_percentile', 'era_percentile', 'xba_percentile', 'xwoba_percentile',
])

// Rate stats (batting-average-shaped, < 1) drop the leading "0" per this
// project's OOTP display convention -- same rule as
// PlayerDetails.vue's formatRate().
const RATE_KEYS = new Set(['xba_percentile', 'xwoba_percentile'])

function getStatValue(key: string): string | undefined {
  if (!PROJECTED_STAT_KEYS.has(key)) return undefined
  const raw = xStatsPitch.value?.[key.replace('_percentile', '_value')]
  if (raw === null || raw === undefined) return undefined
  const num = Number(raw)
  if (RATE_KEYS.has(key)) return num.toFixed(3).replace(/^0\./, '.')
  if (key === 'era_percentile') return num.toFixed(2)
  if (key === 'pitching_runs_percentile') return num.toFixed(1)
  return String(Math.round(num))
}

function formatYear(dateString: string): string {
  const date = new Date(dateString)
  return date.getFullYear().toString()
}

async function getYears() {
  if (!years.value) {
    const yearsRes = await fetch(`/api/players/${props.playerId}/ratings?years=true`)
    if (yearsRes.ok) {
      years.value = await yearsRes.json()
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

    const pitchRes = await fetch(`/api/players/ratings/${ratingId}/expected/pitching/percentiles?mlb=${mlbComp.value}`)
    xStatsPitch.value = pitchRes.ok ? await pitchRes.json() : null
    if (!pitchRes.ok) throw new Error('Failed to load expected pitching stats.')

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

      <div v-if='xStatsPitch'>
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
        <template v-for="[key, value] in sortedEntries(xStatsPitch, valueOrder)" :key="key">
          <PercentileBar :label="getStatLabel(key)" :percentile="Number(value)" :value="getStatValue(key)" />
        </template>
      </div>

      <div v-if='xStatsPitch'>
        <div class="relative w-full h-10">
          <div class="absolute inset-x-0 bottom-1.25 h-0.5 bg-teal-600"></div>

          <div class="relative flex items-center space-x-2 h-full px-4">
            <img src="@/assets/slider-pitcher.png" class="w-10 h-10" />
            <h3 class="text-base font-semibold">Pitching</h3>
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
        <template v-for="[key, value] in sortedEntries(xStatsPitch, pitchingOrder)" :key="key">
          <PercentileBar :label="getStatLabel(key)" :percentile="Number(value)" :value="getStatValue(key)" />
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
