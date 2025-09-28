<template>
  <div>
    <div v-if="loading">Loading...</div>
    <div v-else-if="error">{{ error }}</div>
    <div v-else>
      <h2>Percentiles</h2>

      <div v-if="xStatsBat">
        <h3>Batting</h3>
        <template v-for="(value, key) in xStatsBat" :key="key">
          <PercentileBar
            v-if="isValidPercentile(value)"
            :label="String(key)"
            :percentile="Number(value)"
          />
        </template>
      </div>

      <div v-if="xStatsRun">
        <h3>Base Running</h3>
        <template v-for="(value, key) in xStatsRun" :key="key">
          <PercentileBar
            v-if="isValidPercentile(value)"
            :label="String(key)"
            :percentile="Number(value)"
          />
        </template>
      </div>

      <div v-if="filteredFieldingPercentiles">
        <h3>Fielding</h3>
        <template v-for="(value, key) in filteredFieldingPercentiles" :key="key">
            <PercentileBar
            :label="String(key)"
            :percentile="Number(value)"
            />
        </template>
        </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import PercentileBar from './PercentileBar.vue'

const props = defineProps<{ playerId: number }>()
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
    // 1. Fetch most recent player rating ID
    const ratingRes = await fetch(`/api/players/${props.playerId}/ratings?latest=true`)
    if (ratingRes.ok) {
      playerRating.value = await ratingRes.json()
      console.log(playerRating.value)
    } else {
      error.value = 'Failed to load player rating info.'
      return
    }

    if (!playerRating.value || !playerRating.value.rating_id) {
      throw new Error('Player rating data is missing or invalid.')
    }

    const ratingId = playerRating.value.rating_id

    const batRes = await fetch(`/api/players/stats/expected/batting/${ratingId}/percentiles`)
    if (batRes.ok) {
      xStatsBat.value = await batRes.json()
      console.log(xStatsBat.value)
    } else {
      error.value = 'Failed to load expected batting stats.'
    }

    // 3. Fetch expected basepath stats
    const runRes = await fetch(`/api/players/stats/expected/basepath/${ratingId}/percentiles`)
    if (runRes.ok) {
      xStatsRun.value = await runRes.json()
      console.log(xStatsRun.value)
    } else {
      error.value = 'Failed to load expected basepath stats.'
    }

    // 4. Fetch expected fielding stats
    const fieldRes = await fetch(`/api/players/stats/expected/fielding/${ratingId}/percentiles`)
    if (fieldRes.ok) {
      xStatsField.value = await fieldRes.json()
      console.log(xStatsField.value)
    } else {
      error.value = 'Failed to load expected fielding stats.'
    }
  } catch (err: any) {
    error.value = err.message || 'An error occurred.'
  } finally {
    loading.value = false
  }
})

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