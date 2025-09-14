<script setup lang="ts">
import { ref, onMounted } from 'vue'

const props = defineProps<{ playerId: number }>()

const playerDetails = ref<any>(null)
const loading = ref(true)
const error = ref<string | null>(null)

onMounted(async () => {
  try {
    const response = await fetch(`/api/players/${props.playerId}/details`)
    if (response.ok) {
      playerDetails.value = await response.json()
    } else {
      error.value = 'Failed to load player details.'
    }
  } catch (err) {
    error.value = 'Failed to load player details.'
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
    <div>
      <ul v-if="playerDetails && playerDetails.battingStats">
        <li v-for="(stat, idx) in playerDetails.battingStats" :key="idx">
          {{ stat.year }}: {{ stat.stats }}
        </li>
      </ul>
      <ul v-else>
        <li>batting stats year -3</li>
        <li>batting stats year -2</li>
        <li>batting stats year -1</li>
        <li>batting career stats</li>
      </ul>
    </div>
    <div v-if="loading">Loading...</div>
    <div v-if="error">{{ error }}</div>
  </div>
</template>