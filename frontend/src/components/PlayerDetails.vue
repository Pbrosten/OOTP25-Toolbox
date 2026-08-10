<script setup lang="ts">
import { ref, onMounted, computed, defineExpose } from 'vue'

const props = defineProps<{ playerId: number }>()

const playerDetails = ref<any>(null)
const battingStats = ref<any[]>([])
const pitchingStats = ref<any[]>([])
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

    if (playerDetails.value?.position === 'P') {
      const pitchingRes = await fetch(`/api/players/${props.playerId}/career/pitching`)
      if (pitchingRes.ok) {
        const rawPitching = await pitchingRes.json()
        const numericKeys = ['w', 'l', 's', 'g', 'gs', 'outs', 'k', 'bb', 'ha', 'er']
        pitchingStats.value = rawPitching.map((row: any) => {
          const normalized = { ...row }
          for (const key of numericKeys) normalized[key] = Number(row[key])
          return normalized
        })
      }
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

const recentPitchingStats = computed(() => {
  if (!pitchingStats.value.length) return []
  return [...pitchingStats.value]
    .sort((a, b) => Number(b.year) - Number(a.year))
    .slice(0, maxRows)
})

// IP is displayed in OOTP's thirds notation (e.g. "132.1"), not decimal --
// derived from `outs` (exact) rather than the API's `ip` column, which is
// pre-floored to whole innings and would silently drop the .1/.2 remainder.
// A whole-inning total (remainder 0) drops the decimal entirely ("132", not
// "132.0"), matching the reference screenshot's per-season IP column.
function calcIpDisplay(stat: any): string {
  const wholeInnings = Math.floor(stat.outs / 3)
  const remainder = stat.outs % 3
  return remainder === 0 ? `${wholeInnings}` : `${wholeInnings}.${remainder}`
}

function calcEra(stat: any): number | null {
  return stat.outs > 0 ? (9 * stat.er) / (stat.outs / 3) : null
}

function calcWhip(stat: any): number | null {
  return stat.outs > 0 ? (stat.bb + stat.ha) / (stat.outs / 3) : null
}

// Unlike AVG/OBP/SLG, ERA and WHIP conventionally keep their leading digit
// (e.g. "3.60", not ".360"), so this doesn't strip a leading "0.".
function formatEraWhip(value: number | null): string {
  if (value === null) return '-'
  return value.toFixed(2)
}

const pitchingTotals = computed(() => {
  if (!pitchingStats.value.length) return null

  const sum = (key: string) =>
    pitchingStats.value.reduce((acc, s) => acc + (Number(s[key]) || 0), 0)

  const totalsStat = {
    w: sum('w'),
    l: sum('l'),
    s: sum('s'),
    g: sum('g'),
    gs: sum('gs'),
    outs: sum('outs'),
    k: sum('k'),
    bb: sum('bb'),
    ha: sum('ha'),
    er: sum('er'),
  }

  return {
    totalW: totalsStat.w,
    totalL: totalsStat.l,
    totalS: totalsStat.s,
    totalG: totalsStat.g,
    totalGS: totalsStat.gs,
    totalK: totalsStat.k,
    ip: calcIpDisplay(totalsStat),
    era: calcEra(totalsStat),
    whip: calcWhip(totalsStat),
    seasons: new Set(pitchingStats.value.map((s) => s.year)).size,
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

    <template v-if="playerDetails && playerDetails.position === 'P'">
      <h2 class="text-2xl font-semibold mb-4">
        Career Pitching Stats
        <span v-if="playerDetails">
          ({{ playerDetails.league_id === 203 ? 'MLB' : 'MiLB' }})
        </span>
      </h2>
      <table class="w-full max-w-4xl table-auto border-collapse text-sm mb-6">
        <thead>
          <tr class="bg-gray-200 text-gray-700">
            <th class="px-2 py-1">Year</th>
            <th class="px-2 py-1">Team</th>
            <th class="px-2 py-1">W</th>
            <th class="px-2 py-1">L</th>
            <th class="px-2 py-1">ERA</th>
            <th class="hidden lg:table-cell px-2 py-1">G</th>
            <th class="hidden lg:table-cell px-2 py-1">GS</th>
            <th class="px-2 py-1">SV</th>
            <th class="px-2 py-1">IP</th>
            <th class="px-2 py-1">SO</th>
            <th class="px-2 py-1">WHIP</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="stat in recentPitchingStats" :key="stat.year + '-' + stat.abbr" class="even:bg-gray-50">
            <td class="px-2 py-1">{{ stat.year }}</td>
            <td class="px-2 py-1">{{ stat.abbr }}</td>
            <td class="px-2 py-1">{{ stat.w }}</td>
            <td class="px-2 py-1">{{ stat.l }}</td>
            <td class="px-2 py-1">{{ formatEraWhip(calcEra(stat)) }}</td>
            <td class="hidden lg:table-cell px-2 py-1">{{ stat.g }}</td>
            <td class="hidden lg:table-cell px-2 py-1">{{ stat.gs }}</td>
            <td class="px-2 py-1">{{ stat.s }}</td>
            <td class="px-2 py-1">{{ calcIpDisplay(stat) }}</td>
            <td class="px-2 py-1">{{ stat.k }}</td>
            <td class="px-2 py-1">{{ formatEraWhip(calcWhip(stat)) }}</td>
          </tr>

          <!-- Totals row -->
          <template v-if="pitchingTotals">
            <tr class="bg-gray-100 font-bold lg:hidden">
              <td class="px-2 py-1" colspan="2">{{ pitchingTotals.seasons }} Seasons</td>
              <td class="px-2 py-1">{{ pitchingTotals.totalW }}</td>
              <td class="px-2 py-1">{{ pitchingTotals.totalL }}</td>
              <td class="px-2 py-1">{{ formatEraWhip(pitchingTotals.era) }}</td>
              <td class="px-2 py-1">{{ pitchingTotals.totalS }}</td>
              <td class="px-2 py-1">{{ pitchingTotals.ip }}</td>
              <td class="px-2 py-1">{{ pitchingTotals.totalK }}</td>
              <td class="px-2 py-1">{{ formatEraWhip(pitchingTotals.whip) }}</td>
            </tr>
            <tr class="bg-gray-100 font-bold hidden lg:table-row">
              <td class="px-2 py-1" colspan="2">{{ pitchingTotals.seasons }} Seasons</td>
              <td class="px-2 py-1">{{ pitchingTotals.totalW }}</td>
              <td class="px-2 py-1">{{ pitchingTotals.totalL }}</td>
              <td class="px-2 py-1">{{ formatEraWhip(pitchingTotals.era) }}</td>
              <td class="px-2 py-1">{{ pitchingTotals.totalG }}</td>
              <td class="px-2 py-1">{{ pitchingTotals.totalGS }}</td>
              <td class="px-2 py-1">{{ pitchingTotals.totalS }}</td>
              <td class="px-2 py-1">{{ pitchingTotals.ip }}</td>
              <td class="px-2 py-1">{{ pitchingTotals.totalK }}</td>
              <td class="px-2 py-1">{{ formatEraWhip(pitchingTotals.whip) }}</td>
            </tr>
          </template>
        </tbody>
      </table>
    </template>

    <div v-if="loading" class="text-gray-500 text-sm">Loading...</div>
    <div v-if="error" class="text-red-500 text-sm mt-2">{{ error }}</div>
  </div>
</template>
