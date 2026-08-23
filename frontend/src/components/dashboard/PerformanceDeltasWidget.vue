<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useCurrentTeam } from '@/composables/useCurrentTeam'
import { useActionQueue } from '@/composables/useActionQueue'
import { fetchTeamPerformanceDeltas, type PerformanceDeltaPlayer } from '@/api/teams'

// GM Command Center's over/underperformers widget (ticket 0080) --
// scoped to whichever team useCurrentTeam() currently points at, same
// pattern as the other dashboard widgets. The backend already filters
// to notable deltas only (PERFORMANCE_DELTA_NOTABLE_THRESHOLD) and
// requires a qualifying real-stat sample this season -- this widget just
// splits that list into over-/under-performing and renders it, same
// two-column layout as RosterWeaknessesWidget.vue (ticket 0081).
const { currentTeamId } = useCurrentTeam()
const { setAlerts } = useActionQueue()

const players = ref<PerformanceDeltaPlayer[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

watch(currentTeamId, fetchDeltas, { immediate: true })

async function fetchDeltas() {
  if (currentTeamId.value === null) {
    loading.value = false
    players.value = []
    error.value = null
    return
  }

  loading.value = true
  error.value = null

  try {
    const data = await fetchTeamPerformanceDeltas(currentTeamId.value)
    players.value = data.players
  } catch (err: any) {
    error.value = err.message || 'An error occurred.'
  } finally {
    loading.value = false
  }
}

// The backend already returns delta descending -- overperformers keep
// that order (biggest delta first); underperformers reverse it so the
// most notable underperformance leads that column too.
const overperformers = computed(() => players.value.filter((p) => p.delta > 0))
const underperformers = computed(() =>
  players.value.filter((p) => p.delta < 0).slice().reverse(),
)

// Action Queue (ticket 0084): every returned player is already a
// notable delta (backend-filtered) -- both directions are alert-worthy,
// an overperformer is a buy-low-extend opportunity, an underperformer a
// concern worth watching.
watch(
  players,
  (list) => {
    setAlerts(
      'performance-deltas',
      list.map((p) => ({
        category: 'Performance',
        message:
          p.delta > 0
            ? `${playerName(p)} is overperforming projection by ${formatDelta(p.delta)} WAR`
            : `${playerName(p)} is underperforming projection by ${formatDelta(p.delta)} WAR`,
        link: `/players/${p.player_id}`,
      })),
    )
  },
  { immediate: true },
)

function playerName(p: PerformanceDeltaPlayer): string {
  return `${p.first_name} ${p.last_name}`
}

function formatWar(value: number): string {
  return value.toFixed(1)
}

function formatDelta(value: number): string {
  return value > 0 ? `+${value.toFixed(1)}` : value.toFixed(1)
}
</script>

<template>
  <div class="rounded bg-gray-50 p-4">
    <div v-if="loading" class="text-gray-500 text-sm">Loading...</div>
    <div v-else-if="error" class="text-red-500 text-sm">{{ error }}</div>
    <div v-else-if="currentTeamId === null" class="text-gray-500 text-sm">No team selected.</div>

    <div v-else class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div>
        <h3 class="text-sm font-semibold text-gray-700 mb-2">Overperforming</h3>
        <p v-if="overperformers.length === 0" class="text-sm text-gray-400 italic">
          No notable overperformers.
        </p>
        <ul v-else class="space-y-1">
          <li
            v-for="p in overperformers"
            :key="p.player_id"
            class="flex items-center justify-between px-2 py-1 rounded bg-team-subtle text-team text-sm"
            :title="`${formatWar(p.actual_war)} actual WAR vs ${formatWar(p.projected_war)} projected`"
          >
            <router-link :to="`/players/${p.player_id}`" class="hover:underline">
              {{ playerName(p) }}
            </router-link>
            <span class="shrink-0 ml-2 font-medium">{{ formatDelta(p.delta) }} WAR</span>
          </li>
        </ul>
      </div>

      <div>
        <h3 class="text-sm font-semibold text-gray-700 mb-2">Underperforming</h3>
        <p v-if="underperformers.length === 0" class="text-sm text-gray-400 italic">
          No notable underperformers.
        </p>
        <ul v-else class="space-y-1">
          <li
            v-for="p in underperformers"
            :key="p.player_id"
            class="flex items-center justify-between px-2 py-1 rounded bg-red-50 text-red-900 text-sm"
            :title="`${formatWar(p.actual_war)} actual WAR vs ${formatWar(p.projected_war)} projected`"
          >
            <router-link :to="`/players/${p.player_id}`" class="hover:underline">
              {{ playerName(p) }}
            </router-link>
            <span class="shrink-0 ml-2 font-medium">{{ formatDelta(p.delta) }} WAR</span>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>
