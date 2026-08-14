<script setup lang="ts">
import { ref, onMounted } from 'vue'

const props = defineProps<{ playerId: number }>()

interface DevelopmentAlert {
  table: string
  column: string
  direction: 'improved' | 'declined'
  delta: number
  message: string
}

// Only `trends.length` is used (to tell "not enough history yet" apart
// from "history exists, nothing notable happened" -- both cases return an
// empty alerts list, so that distinction needs 0050's row count). The
// trend rows themselves are never rendered -- the per-category delta
// breakdown was dropped in favor of notifications-only display.
const hasHistory = ref(false)
const alerts = ref<DevelopmentAlert[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

onMounted(fetchTrends)

async function fetchTrends() {
  loading.value = true
  error.value = null

  try {
    const [trendsRes, alertsRes] = await Promise.all([
      fetch(`/api/players/ratings/${props.playerId}/trends`),
      fetch(`/api/players/ratings/${props.playerId}/trends/alerts`),
    ])
    if (!trendsRes.ok) throw new Error('Failed to load rating trends.')
    if (!alertsRes.ok) throw new Error('Failed to load development alerts.')

    const trends = await trendsRes.json()
    hasHistory.value = trends.length > 0
    alerts.value = await alertsRes.json()
  } catch (err: any) {
    error.value = err.message || 'An error occurred.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="development-trends-wrapper w-full">
    <h2 class="text-lg font-semibold mb-2">Development Trends</h2>
    <div v-if="loading" class="text-gray-500 text-sm">Loading...</div>
    <div v-else-if="error" class="text-red-500 text-sm">{{ error }}</div>

    <template v-else>
      <!-- Fewer than 4 recorded heaps: 0050 returns an empty trend list,
           not an error. Render an explicit message rather than nothing, so
           it's clear the feature is working, not broken (ticket 0052's
           Design choices). -->
      <div v-if="!hasHistory" class="text-gray-500 text-sm">
        Not enough history yet — development trends need at least 4 recorded
        months for this player.
      </div>

      <template v-else>
        <div v-if="alerts.length > 0" class="flex flex-col gap-2">
          <div
            v-for="alert in alerts"
            :key="alert.table + '-' + alert.column"
            class="text-sm px-3 py-2 rounded border-l-4"
            :class="alert.direction === 'improved'
              ? 'border-teal-600 bg-teal-50 text-teal-900'
              : 'border-red-500 bg-red-50 text-red-900'"
          >
            {{ alert.message }}
          </div>
        </div>
        <div v-else class="text-sm text-gray-500">
          No notable rating changes over the last 3 months.
        </div>
      </template>
    </template>
  </div>
</template>

<style scoped>
.development-trends-wrapper {
  width: 100%;
}
</style>
