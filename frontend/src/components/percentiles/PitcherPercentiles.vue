<script setup lang='ts'>
import { ref, onMounted, watch } from 'vue'
import {
  Listbox,
  ListboxLabel,
  ListboxButton,
  ListboxOptions,
  ListboxOption,
} from '@headlessui/vue'
import { CheckIcon, ChevronUpDownIcon } from '@heroicons/vue/20/solid'
import PercentileBar from './PercentileBar.vue'

const props = defineProps<{ playerId: number, leagueId: number | null }>()

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

// OOTP's 1-20 fastball-velocity rating index -> displayed MPH band. Not
// derived from any exported column -- it's a fixed UI convention baked into
// the game itself, so it lives here as a plain lookup rather than a DB table.
const VELOCITY_MAP: Record<number, string> = {
  20: '100+',
  19: '99-101',
  18: '98-100',
  17: '97-99',
  16: '96-98',
  15: '95-97',
  14: '94-96',
  13: '93-95',
  12: '92-94',
  11: '91-93',
  10: '90-92',
  9: '89-91',
  8: '88-90',
  7: '87-89',
  6: '86-88',
  5: '85-87',
  4: '84-86',
  3: '83-85',
  2: '80-83',
  1: '75-80',
}

const xStatsPitch = ref<any>(null)

const loading = ref(true)
const error = ref<string | null>(null)

const years = ref<any>(null)
const selectedYear = ref(null)

onMounted(() => {
  fetchPercentiles()
  getYears()
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
// no raw number. velocity_percentile is the one exception: its "Fastball
// Velo" label isn't borrowed from an unrelated stat, it's literally what the
// underlying 1-20 rating encodes, so its raw value is handled separately
// below via VELOCITY_MAP rather than through this set.
const PROJECTED_STAT_KEYS = new Set([
  'pitching_runs_percentile', 'era_percentile', 'xba_percentile', 'xwoba_percentile',
])

// Rate stats (batting-average-shaped, < 1) drop the leading "0" per this
// project's OOTP display convention -- same rule as
// PlayerDetails.vue's formatRate().
const RATE_KEYS = new Set(['xba_percentile', 'xwoba_percentile'])

function getStatValue(key: string): string | undefined {
  if (key === 'velocity_percentile') {
    const raw = xStatsPitch.value?.velocity_value
    if (raw === null || raw === undefined) return undefined
    return VELOCITY_MAP[Number(raw)]
  }
  if (!PROJECTED_STAT_KEYS.has(key)) return undefined
  const raw = xStatsPitch.value?.[key.replace('_percentile', '_value')]
  if (raw === null || raw === undefined) return undefined
  const num = Number(raw)
  if (RATE_KEYS.has(key)) return num.toFixed(3).replace(/^0\./, '.')
  if (key === 'era_percentile') return num.toFixed(2)
  if (key === 'pitching_runs_percentile') return num.toFixed(1)
  return String(Math.round(num))
}

// Ticket 0086: mechanical `${key}_potential` lookup, same convention as
// BatterPercentiles.vue's getPotentialPercentile(). A key with no
// talent-grade counterpart (stamina/hold/velocity have none in
// players_pitching_talent) just resolves to undefined -> null, same
// "no shadow" outcome as the current percentile already being the ceiling.
function getPotentialPercentile(key: string): number | null {
  const raw = xStatsPitch.value?.[`${key}_potential`]
  return raw === null || raw === undefined ? null : Number(raw)
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

    const pitchRes = await fetch(`/api/players/ratings/${ratingId}/expected/pitching/percentiles`)
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
        <Listbox v-model="selectedYear">
          <div class="relative mt-1">
            <ListboxButton
              class="min-w-[5rem] w-auto cursor-default rounded-lg bg-white py-2 pl-3 pr-10 text-left shadow-md focus:outline-none focus-visible:border-indigo-500 focus-visible:ring-2 focus-visible:ring-white/75 focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--team-bg)] sm:text-sm">
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
                    active ? 'bg-team-subtle text-team' : 'text-gray-900',
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
          <div class="absolute inset-x-0 bottom-1.25 h-0.5 bg-team"></div>

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
          <PercentileBar
            :label="getStatLabel(key)"
            :percentile="Number(value)"
            :value="getStatValue(key)"
            :potential-percentile="getPotentialPercentile(key)"
          />
        </template>
      </div>

      <div v-if='xStatsPitch'>
        <div class="relative w-full h-10">
          <div class="absolute inset-x-0 bottom-1.25 h-0.5 bg-team"></div>

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
          <PercentileBar
            :label="getStatLabel(key)"
            :percentile="Number(value)"
            :value="getStatValue(key)"
            :potential-percentile="getPotentialPercentile(key)"
          />
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
