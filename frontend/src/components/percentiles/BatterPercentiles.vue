<script setup lang="ts">
import { ref, onMounted } from 'vue'

const props = defineProps<{ playerId: number }>()

const playerRating = ref<any>(null)
const xStatsBat = ref<any>(null)
const xStatsRun = ref<any>(null)
const xStatsField = ref<any>(null)

const loading = ref(true)
const error = ref<string | null>(null)

onMounted(async () => {
    loading.value = true
    error.value = null
    try {
        // Fetch most recent player rating id
        const ratingRes = await fetch(`/api/players/${props.playerId}/ratings?latest=true`)
        if (ratingRes.ok) {
            playerRating.value = await ratingRes.json()
        } else {
            error.value = 'Failed to load player rating info.'
        }

        if (!playerRating.value || !playerRating.value.rating_id) {
            throw new Error('Player rating data is missing or invalid.')
        }

        const ratingId = playerRating.value.rating_id
        // Fetch expected batting stats
        const batRes = await fetch(`/api/players/stats/expected/batting/${ratingId}/percentiles`)
        if (batRes.ok) {
            xStatsBat.value = await batRes.json()
        } else {
            error.value = 'Failed to load expected batting stats.'
        }
        // Fetch expected batting stats
        const runRes = await fetch(`/api/players/stats/expected/basepath/${ratingId}/percentiles`)
        if (runRes.ok) {
            xStatsRun.value = await runRes.json()
        } else {
            error.value = 'Failed to load expected basepath stats.'
        }
        // Fetch expected batting stats
        const fieldRes = await fetch(`/api/players/stats/expected/fielding/${ratingId}/percentiles`)
        if (fieldRes.ok) {
            xStatsField.value = await fieldRes.json()
        } else {
            error.value = 'Failed to load expected fielding stats.'
        }
    } finally {
        loading.value = false
    }
})
</script>

<template>
  <div>
    <div v-if="loading">Loading...</div>
    <div v-else-if="error">{{ error }}</div>
    <div v-else>
      <h2>Percentiles</h2>
      <div>
        <pre>{{ xStatsBat }}</pre>
        <pre>{{ xStatsRun }}</pre>
        <pre>{{ xStatsField }}</pre>
      </div>
    </div>
  </div>
</template>
// Process for touching DB
// 1. find most recent rating id by player id
// 2. pull expected batting stats by rating id
// 3. pull expected basepah stats by rating id
// 4. pull expected fielding stats by rating id
// 5. format data and visualize