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
  if (!battingStats.value.length) {
    return null
  }
  // Defensive: ensure all fields exist and are numbers
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

  // Batting average
  const avg = totalAB > 0 ? totalH / totalAB : null
  // OBP
  const obp = totalPA > 0 ? (totalH + totalBB + totalHP) / totalPA : null
  // SLG
  const slg = totalAB > 0 ? (totalH + totalD + (2 * totalT) + (3 * totalHR)) / totalAB : null
  // OPS
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
  <div>
    <!-- <a id="player-picture">
      <img src="/baseball.png" class="logo" alt="Player picture" />
    </a> -->
    <h1>
      <span v-if="playerDetails"> {{ playerDetails.first_name}} {{ playerDetails.last_name }} </span>
      <span v-else> {{ playerId }} </span>
    </h1>
    <span>
      <p v-if="playerDetails">
        {{ playerDetails.position }} | Bats/Throws: {{ playerDetails.bats }}/{{ playerDetails.throws }} |
        {{ playerDetails.height }}CM {{ playerDetails.weight }}LBS| Age: {{ playerDetails.age }}
      </p>
      <p v-else>Player Position | Bats/Throws: R/R | Height Weight | Age: ##</p>
    </span>
    <h2>Career Batting Stats</h2>
    <table v-if="recentStats.length">
      <thead>
        <tr>
          <th>Year</th>
          <th>Team</th>
          <th>PA</th>
          <th>AB</th>
          <th>R</th>
          <th>H</th>
          <th>HR</th>
          <th>SB</th>
          <th>AVG</th>
          <th>OBP</th>
          <th>SLG</th>
          <th>OPS</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="stat in recentStats" :key="stat.year + '-' + stat.abbr">
          <td>{{ stat.year }}</td>
          <td>{{ stat.abbr }}</td>
          <td>{{ stat.pa }}</td>
          <td>{{ stat.ab }}</td>
          <td>{{ stat.r }}</td>
          <td>{{ stat.h }}</td>
          <td>{{ stat.hr }}</td>
          <td>{{ stat.sb }}</td>
          <td>
            <span v-if="stat.ab > 0">
              .{{ ((stat.h / stat.ab).toFixed(3)).split('.')[1] }}
            </span>
            <span v-else>
              -
            </span>
          </td>
          <td>
            <span v-if="stat.pa > 0">
              .{{ (( (stat.h + stat.bb + stat.hp) / stat.pa ).toFixed(3)).split('.')[1] }}
            </span>
            <span v-else>
              -
            </span>
          </td>
          <td>
            <span v-if="stat.ab > 0">
              .{{ (( (stat.h + stat.d + (2 * stat.t) + (3 * stat.hr)) / stat.ab ).toFixed(3)).split('.')[1] }}
            </span>
            <span v-else>
              -
            </span>
          </td>
          <td>
            <span v-if="stat.pa > 0">
              .{{ (( ( (stat.h + stat.bb + stat.hp) / stat.pa ) + ( (stat.h + stat.d + (2 * stat.t) + (3 * stat.hr)) / stat.ab ) ).toFixed(3)).split('.')[1] }}
            </span>
            <span v-else>
              -
            </span>
          </td>
        </tr>
        <!-- Totals row -->
        <tr v-if="totals" style="font-weight: bold; background: #f0f0f0;">
          <td colspan="2">Total</td>
          <td>{{ totals.totalPA }}</td>
          <td>{{ totals.totalAB }}</td>
          <td>{{ totals.totalR }}</td>
          <td>{{ totals.totalH }}</td>
          <td>{{ totals.totalHR }}</td>
          <td>{{ totals.totalSB }}</td>
          <td>
            <span v-if="totals.avg !== null">
              .{{ (totals.avg.toFixed(3)).split('.')[1] }}
            </span>
            <span v-else>-</span>
          </td>
          <td>
            <span v-if="totals.obp !== null">
              .{{ (totals.obp.toFixed(3)).split('.')[1] }}
            </span>
            <span v-else>-</span>
          </td>
          <td>
            <span v-if="totals.slg !== null">
              .{{ (totals.slg.toFixed(3)).split('.')[1] }}
            </span>
            <span v-else>-</span>
          </td>
          <td>
            <span v-if="totals.ops !== null">
              .{{ (totals.ops.toFixed(3)).split('.')[1] }}
            </span>
            <span v-else>-</span>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-if="loading">Loading...</div>
    <div v-if="error">{{ error }}</div>
  </div>
</template>