<script setup lang="ts">
import { ref, onMounted, computed, defineExpose } from 'vue'

const props = defineProps<{ playerId: number }>()

const playerDetails = ref<any>(null)
const battingStats = ref<any[]>([])
const maxRows = 5
const loading = ref(true)
const error = ref<string | null>(null)

onMounted(async () => {
  loading.value = true
  error.value = null
  try {
    const [detailsRes, statsRes] = await Promise.all([
      fetch(`/api/players/${props.playerId}/details`),
      fetch(`/api/players/${props.playerId}/career/batting`)
    ])

    if (detailsRes.ok) {
      playerDetails.value = await detailsRes.json()
    } else {
      error.value = 'Failed to load player details.'
    }

    if (statsRes.ok) {
      const rawStats = await statsRes.json()
      // The API returns SQL SUM() results as JSON strings (e.g. "ab": "558"),
      // not numbers. Left uncoerced, "+" on these fields concatenates
      // instead of adding wherever a formula chains more than one of them
      // (e.g. calcSlg's h+d+... produced six-digit "stats" instead of a
      // real quotient). Normalize once here so every consumer below --
      // per-row calc functions and the totals sum() alike -- works with
      // real numbers.
      const numericKeys = ['pa', 'ab', 'r', 'h', 'hr', 'sb', 'bb', 'hp', 'sf', 'd', 't']
      battingStats.value = rawStats.map((row: any) => {
        const normalized = { ...row }
        for (const key of numericKeys) normalized[key] = Number(row[key])
        return normalized
      })
    } else {
      error.value = 'Failed to load batting stats.'
    }

  } catch (err) {
    error.value = 'Failed to load player data.'
  } finally {
    loading.value = false
  }
})

const recentStats = computed(() => {
  if (!battingStats.value.length) return []
  return [...battingStats.value]
    .sort((a, b) => Number(b.year) - Number(a.year))
    .slice(0, maxRows)
})

// Shared rate-stat formulas -- used for both per-row cells and the totals
// row, so the OBP/SLG/OPS math only lives in one place. Each returns null
// (rather than NaN) when its denominator is 0, so a stint that's e.g. all
// walks (ab === 0) renders "-" for SLG/OPS instead of a NaN cell.
function calcAvg(stat: any): number | null {
  return stat.ab > 0 ? stat.h / stat.ab : null
}

function calcObp(stat: any): number | null {
  // Standard OBP denominator excludes sacrifice hits (SH), even though SH
  // does count toward OOTP's own PA total -- confirmed against real dump
  // data (pa ~= ab+bb+hp+sf+sh). Using `pa` here would understate OBP.
  const denom = stat.ab + stat.bb + stat.hp + stat.sf
  return denom > 0 ? (stat.h + stat.bb + stat.hp) / denom : null
}

function calcSlg(stat: any): number | null {
  return stat.ab > 0 ? (stat.h + stat.d + (2 * stat.t) + (3 * stat.hr)) / stat.ab : null
}

function calcOps(stat: any): number | null {
  const obp = calcObp(stat)
  const slg = calcSlg(stat)
  return (obp !== null && slg !== null) ? obp + slg : null
}

// OOTP convention: values < 1 drop the leading "0" (".298"); OPS routinely
// hits >= 1.000 and should render normally ("1.023"), not lose its leading
// digit -- replace() only strips a leading "0.", unlike the old
// toFixed(3).split('.')[1] approach, which mangled any value >= 1.
function formatRate(value: number | null): string {
  if (value === null) return '-'
  return value.toFixed(3).replace(/^0\./, '.')
}

const totals = computed(() => {
  if (!battingStats.value.length) return null

  const sum = (key: string) =>
    battingStats.value.reduce((acc, s) => acc + (Number(s[key]) || 0), 0)

  const totalsStat = {
    pa: sum('pa'),
    ab: sum('ab'),
    r: sum('r'),
    h: sum('h'),
    hr: sum('hr'),
    sb: sum('sb'),
    bb: sum('bb'),
    hp: sum('hp'),
    sf: sum('sf'),
    d: sum('d'),
    t: sum('t'),
  }

  return {
    totalPA: totalsStat.pa,
    totalAB: totalsStat.ab,
    totalR: totalsStat.r,
    totalH: totalsStat.h,
    totalHR: totalsStat.hr,
    totalSB: totalsStat.sb,
    avg: calcAvg(totalsStat),
    obp: calcObp(totalsStat),
    slg: calcSlg(totalsStat),
    ops: calcOps(totalsStat),
  }
})

defineExpose({
  playerDetails
})
</script>

<template>
  <div class="flex flex-col items-center text-center p-4 w-full">
    <h1 class="text-3xl mb-2">
      <span v-if="playerDetails">{{ playerDetails.first_name }} {{ playerDetails.last_name }}</span>
      <span v-else>{{ playerId }}</span>
    </h1>
    <h2 class="text-xl mb-2">
      <div v-if="playerDetails">
        {{ playerDetails.position }}
        <span class="text-teal-800">|</span>
        {{ playerDetails.team_city }} {{ playerDetails.team_name }}
      </div>
    </h2>

    <p class="text-sm text-gray-600 mb-6">
      <div v-if="playerDetails">
        Bats/Throws: {{ playerDetails.bats }}/{{ playerDetails.throws }}
        <span class="text-lg text-teal-800">|</span>
        {{ playerDetails.height }}CM {{ playerDetails.weight }}LBS
        <span class="text-lg text-teal-800">|</span>
        Age: {{ playerDetails.age }}
      </div>
      <div v-else>Player Position
        <span class="text-lg text-teal-800">|</span>  Bats/Throws: R/R
        <span class="text-lg text-teal-800">|</span>  Height Weight
        <span class="text-lg text-teal-800">|</span>  Age: ##</div>
    </p>

    <template v-if="playerDetails && playerDetails.position !== 'P'">
      <h2 class="text-2xl font-semibold mb-4">
        Career Batting Stats
        <span v-if="playerDetails">
          ({{ playerDetails.league_id === 203 ? 'MLB' : 'MiLB' }})
        </span>
      </h2>
      <table class="w-full max-w-4xl table-auto border-collapse text-sm mb-6">
        <thead>
          <tr class="bg-gray-200 text-gray-700">
            <th class="px-2 py-1">Year</th>
            <th class="px-2 py-1">Team</th>
            <th class="hidden lg:table-cell px-2 py-1">PA</th>
            <th class="hidden lg:table-cell px-2 py-1">AB</th>
            <th class="hidden lg:table-cell px-2 py-1">R</th>
            <th class="hidden sm:table-cell px-2 py-1">H</th>
            <th class="px-2 py-1">HR</th>
            <th class="px-2 py-1">SB</th>
            <th class="px-2 py-1">AVG</th>
            <th class="hidden sm:table-cell px-2 py-1">OBP</th>
            <th class="hidden sm:table-cell px-2 py-1">SLG</th>
            <th class="px-2 py-1">OPS</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="stat in recentStats" :key="stat.year + '-' + stat.abbr" class="even:bg-gray-50">
            <td class="px-2 py-1">{{ stat.year }}</td>
            <td class="px-2 py-1">{{ stat.abbr }}</td>
            <td class="hidden lg:table-cell px-2 py-1">{{ stat.pa }}</td>
            <td class="hidden lg:table-cell px-2 py-1">{{ stat.ab }}</td>
            <td class="hidden lg:table-cell px-2 py-1">{{ stat.r }}</td>
            <td class="hidden sm:table-cell px-2 py-1">{{ stat.h }}</td>
            <td class="px-2 py-1">{{ stat.hr }}</td>
            <td class="px-2 py-1">{{ stat.sb }}</td>
            <td class="px-2 py-1">{{ formatRate(calcAvg(stat)) }}</td>
            <td class="hidden sm:table-cell px-2 py-1">{{ formatRate(calcObp(stat)) }}</td>
            <td class="hidden sm:table-cell px-2 py-1">{{ formatRate(calcSlg(stat)) }}</td>
            <td class="px-2 py-1">{{ formatRate(calcOps(stat)) }}</td>
          </tr>

          <!-- Totals row -->
          <template v-if="totals">
            <tr class="bg-gray-100 font-bold sm:hidden">
              <td class="px-2 py-1" colspan="2">Total</td>
              <td class="px-2 py-1">{{ totals.totalHR }}</td>
              <td class="px-2 py-1">{{ totals.totalSB }}</td>
              <td class="px-2 py-1">{{ formatRate(totals.avg) }}</td>
              <td class="px-2 py-1">{{ formatRate(totals.ops) }}</td>
            </tr>
            <tr class="bg-gray-100 font-bold hidden sm:table-row lg:hidden">
              <td class="px-2 py-1" colspan="2">Total</td>
              <td class="px-2 py-1">{{ totals.totalH }}</td>
              <td class="px-2 py-1">{{ totals.totalHR }}</td>
              <td class="px-2 py-1">{{ totals.totalSB }}</td>
              <td class="px-2 py-1">{{ formatRate(totals.avg) }}</td>
              <td class="px-2 py-1">{{ formatRate(totals.obp) }}</td>
              <td class="px-2 py-1">{{ formatRate(totals.slg) }}</td>
              <td class="px-2 py-1">{{ formatRate(totals.ops) }}</td>
            </tr>
            <tr class="bg-gray-100 font-bold hidden lg:table-row">
              <td class="px-2 py-1" colspan="4">Total</td>
              <td class="px-2 py-1">{{ totals.totalR }}</td>
              <td class="px-2 py-1">{{ totals.totalH }}</td>
              <td class="px-2 py-1">{{ totals.totalHR }}</td>
              <td class="px-2 py-1">{{ totals.totalSB }}</td>
              <td class="px-2 py-1">{{ formatRate(totals.avg) }}</td>
              <td class="px-2 py-1">{{ formatRate(totals.obp) }}</td>
              <td class="px-2 py-1">{{ formatRate(totals.slg) }}</td>
              <td class="px-2 py-1">{{ formatRate(totals.ops) }}</td>
            </tr>
          </template>
        </tbody>
      </table>
    </template>

    <div v-if="loading" class="text-gray-500 text-sm">Loading...</div>
    <div v-if="error" class="text-red-500 text-sm mt-2">{{ error }}</div>
  </div>
</template>
