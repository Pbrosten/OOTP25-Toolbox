<script setup lang="ts">
import { ref, onMounted } from 'vue'

const props = defineProps<{ playerId: number }>()

const playerDetails = ref<any>(null)
const battingStats = ref<any[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

onMounted(async () => {
  loading.value = true
  error.value = null
  try {
    // Fetch player details
    const detailsRes = await fetch(`/api/players/${props.playerId}/details`)
    if (detailsRes.ok) {
      playerDetails.value = await detailsRes.json()
    } else {
      error.value = 'Failed to load player details.'
    }
    // Fetch batting stats
    const statsRes = await fetch(`/api/players/${props.playerId}/career/batting`)
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
</script>

<template>
  <div>
    <a id="player-picture">
      <img src="/baseball.png" class="logo" alt="Player picture" />
    </a>
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
    <table v-if="battingStats.length">
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
        <tr v-for="stat in battingStats" :key="stat.year + '-' + stat.abbr">
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
      </tbody>
    </table>
    <div v-if="loading">Loading...</div>
    <div v-if="error">{{ error }}</div>
  </div>
</template>