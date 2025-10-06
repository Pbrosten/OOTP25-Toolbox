<script setup lang="ts">
import { ref, onMounted, computed, defineExpose } from 'vue'

const props = defineProps<{ playerId: number }>()

const playerDetails = ref<any>(null)
const battingStats = ref<any[]>([])
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
      battingStats.value = await statsRes.json()
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
    .slice(0, 3)
})

const totals = computed(() => {
  if (!battingStats.value.length) return null

  const sum = (key: string) =>
    battingStats.value.reduce((acc, s) => acc + (Number(s[key]) || 0), 0)

  const totalPA = sum('pa')
  const totalAB = sum('ab')
  const totalR = sum('r')
  const totalH = sum('h')
  const totalHR = sum('hr')
  const totalSB = sum('sb')
  const totalBB = sum('bb')
  const totalHP = sum('hp')
  const totalD = sum('d')
  const totalT = sum('t')

  const avg = totalAB > 0 ? totalH / totalAB : null
  const obp = totalPA > 0 ? (totalH + totalBB + totalHP) / totalPA : null
  const slg = totalAB > 0 ? (totalH + totalD + (2 * totalT) + (3 * totalHR)) / totalAB : null
  const ops = (obp !== null && slg !== null) ? obp + slg : null

  return {
    totalPA,
    totalAB,
    totalR,
    totalH,
    totalHR,
    totalSB,
    avg,
    obp,
    slg,
    ops,
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
            <td class="px-2 py-1">
              <span v-if="stat.ab > 0">.{{ ((stat.h / stat.ab).toFixed(3)).split('.')[1] }}</span>
              <span v-else>-</span>
            </td>
            <td class="hidden sm:table-cell px-2 py-1">
              <span v-if="stat.pa > 0">.{{ (((stat.h + stat.bb + stat.hp) / stat.pa).toFixed(3)).split('.')[1] }}</span>
              <span v-else>-</span>
            </td>
            <td class="hidden sm:table-cell px-2 py-1">
              <span v-if="stat.ab > 0">
                .{{ (((stat.h + stat.d + (2 * stat.t) + (3 * stat.hr)) / stat.ab).toFixed(3)).split('.')[1] }}
              </span>
              <span v-else>-</span>
            </td>
            <td class="px-2 py-1">
              <span v-if="stat.pa > 0">
                .{{ (((stat.h + stat.bb + stat.hp) / stat.pa) + ((stat.h + stat.d + (2 * stat.t) + (3 * stat.hr)) / stat.ab)).toFixed(3).split('.')[1] }}
              </span>
              <span v-else>-</span>
            </td>
          </tr>

          <!-- Totals row -->
          <template v-if="totals">
            <tr class="bg-gray-100 font-bold sm:hidden">
              <td class="px-2 py-1" colspan="2">Total</td>
              <td class="px-2 py-1">{{ totals.totalHR }}</td>
              <td class="px-2 py-1">{{ totals.totalSB }}</td>
              <td class="px-2 py-1">
                <span v-if="totals.avg !== null">.{{ (totals.avg.toFixed(3)).split('.')[1] }}</span>
                <span v-else>-</span>
              </td>
              <td class="px-2 py-1">
                <span v-if="totals.ops !== null">.{{ (totals.ops.toFixed(3)).split('.')[1] }}</span>
                <span v-else>-</span>
              </td>
            </tr>
            <tr class="bg-gray-100 font-bold hidden sm:table-row lg:hidden">
              <td class="px-2 py-1" colspan="2">Total</td>
              <td class="px-2 py-1">{{ totals.totalH }}</td>
              <td class="px-2 py-1">{{ totals.totalHR }}</td>
              <td class="px-2 py-1">{{ totals.totalSB }}</td>
              <td class="px-2 py-1">
                <span v-if="totals.avg !== null">.{{ (totals.avg.toFixed(3)).split('.')[1] }}</span>
                <span v-else>-</span>
              </td>
              <td class="px-2 py-1">
                <span v-if="totals.obp !== null">.{{ (totals.obp.toFixed(3)).split('.')[1] }}</span>
                <span v-else>-</span>
              </td>
              <td class="px-2 py-1">
                <span v-if="totals.slg !== null">.{{ (totals.slg.toFixed(3)).split('.')[1] }}</span>
                <span v-else>-</span>
              </td>
              <td class="px-2 py-1">
                <span v-if="totals.ops !== null">.{{ (totals.ops.toFixed(3)).split('.')[1] }}</span>
                <span v-else>-</span>
              </td>
            </tr>
            <tr class="bg-gray-100 font-bold hidden lg:table-row">
              <td class="px-2 py-1" colspan="4">Total</td>
              <td class="px-2 py-1">{{ totals.totalR }}</td>
              <td class="px-2 py-1">{{ totals.totalH }}</td>
              <td class="px-2 py-1">{{ totals.totalHR }}</td>
              <td class="px-2 py-1">{{ totals.totalSB }}</td>
              <td class="px-2 py-1">
                <span v-if="totals.avg !== null">.{{ (totals.avg.toFixed(3)).split('.')[1] }}</span>
                <span v-else>-</span>
              </td>
              <td class="px-2 py-1">
                <span v-if="totals.obp !== null">.{{ (totals.obp.toFixed(3)).split('.')[1] }}</span>
                <span v-else>-</span>
              </td>
              <td class="px-2 py-1">
                <span v-if="totals.slg !== null">.{{ (totals.slg.toFixed(3)).split('.')[1] }}</span>
                <span v-else>-</span>
              </td>
              <td class="px-2 py-1">
                <span v-if="totals.ops !== null">.{{ (totals.ops.toFixed(3)).split('.')[1] }}</span>
                <span v-else>-</span>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </template>

    <div v-if="loading" class="text-gray-500 text-sm">Loading...</div>
    <div v-if="error" class="text-red-500 text-sm mt-2">{{ error }}</div>
  </div>
</template>
