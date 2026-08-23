<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useCurrentTeam } from '@/composables/useCurrentTeam'
import { useActionQueue } from '@/composables/useActionQueue'
import { fetchTeamRosterStrength, type RosterStrengthGroup } from '@/api/teams'

// GM Command Center's roster weaknesses/surpluses widget (ticket 0081) --
// scoped to whichever team useCurrentTeam() currently points at, same
// pattern as TeamWarWidget.vue (ticket 0079). Only weakness/surplus
// groups are listed -- "neutral" (single adequate starter, neither thin
// nor deep) isn't interesting to flag on a dashboard meant to surface
// what needs attention.
const { currentTeamId } = useCurrentTeam()
const { setAlerts } = useActionQueue()

const groups = ref<RosterStrengthGroup[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

watch(currentTeamId, fetchStrength, { immediate: true })

async function fetchStrength() {
  setAlerts('roster-weaknesses', [])

  if (currentTeamId.value === null) {
    loading.value = false
    groups.value = []
    error.value = null
    return
  }

  loading.value = true
  error.value = null

  try {
    const data = await fetchTeamRosterStrength(currentTeamId.value)
    groups.value = data.groups
    // Action Queue (ticket 0084): only weaknesses are alert-worthy here --
    // a surplus is depth, not something needing the GM's attention.
    setAlerts(
      'roster-weaknesses',
      groups.value
        .filter((g) => g.classification === 'weakness')
        .map((g) => ({
          category: 'Roster',
          message: g.best_player
            ? `${g.group} is thin: ${playerName(g.best_player)} (${formatWar(g.best_war)} WAR)`
            : `${g.group} has no rostered player`,
          link: g.best_player
            ? `/players/${g.best_player.player_id}`
            : `/teams/${currentTeamId.value}/depth-chart`,
        })),
    )
  } catch (err: any) {
    error.value = err.message || 'An error occurred.'
  } finally {
    loading.value = false
  }
}

const weaknesses = computed(() => groups.value.filter((g) => g.classification === 'weakness'))
const surpluses = computed(() => groups.value.filter((g) => g.classification === 'surplus'))

function formatWar(value: number | null): string {
  return value === null ? '—' : value.toFixed(1)
}

function playerName(p: { first_name: string; last_name: string }): string {
  return `${p.first_name} ${p.last_name}`
}

// Native title attribute (same tooltip convention as PercentileBar.vue/
// SurplusValue.vue) -- the rank is supporting detail, not something that
// needs to compete with the name/WAR for space on the list row.
function rankTitle(rank: number, poolSize: number, group: string): string {
  return `#${rank} of ${poolSize} at ${group}`
}
</script>

<template>
  <div class="rounded bg-gray-50 p-4">
    <div v-if="loading" class="text-gray-500 text-sm">Loading...</div>
    <div v-else-if="error" class="text-red-500 text-sm">{{ error }}</div>
    <div v-else-if="currentTeamId === null" class="text-gray-500 text-sm">No team selected.</div>

    <div v-else class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div>
        <h3 class="text-sm font-semibold text-gray-700 mb-2">Weaknesses</h3>
        <p v-if="weaknesses.length === 0" class="text-sm text-gray-400 italic">
          No notable weaknesses.
        </p>
        <ul v-else class="space-y-1">
          <li
            v-for="g in weaknesses"
            :key="g.group"
            class="flex items-center justify-between px-2 py-1 rounded bg-red-50 text-red-900 text-sm"
          >
            <span>
              <span class="font-medium">{{ g.group }}</span> —
              <router-link
                v-if="g.best_player"
                :to="`/players/${g.best_player.player_id}`"
                :title="rankTitle(g.best_player.league_rank, g.league_pool_size, g.group)"
                class="hover:underline decoration-dotted"
              >
                {{ playerName(g.best_player) }}
              </router-link>
              <span v-else>No player rostered</span>
            </span>
            <span class="shrink-0 ml-2">{{ formatWar(g.best_war) }} WAR</span>
          </li>
        </ul>
      </div>

      <div>
        <h3 class="text-sm font-semibold text-gray-700 mb-2">Surpluses</h3>
        <p v-if="surpluses.length === 0" class="text-sm text-gray-400 italic">
          No notable surpluses.
        </p>
        <ul v-else class="space-y-1">
          <li
            v-for="g in surpluses"
            :key="g.group"
            class="px-2 py-1 rounded bg-team-subtle text-team text-sm"
          >
            <span class="font-medium">{{ g.group }}</span> —
            <template v-for="(p, i) in g.surplus_players" :key="p.player_id">
              <router-link
                :to="`/players/${p.player_id}`"
                :title="rankTitle(p.league_rank, g.league_pool_size, g.group)"
                class="hover:underline decoration-dotted"
              >
                {{ playerName(p) }}
              </router-link>
              <span v-if="i < g.surplus_players.length - 1">, </span>
            </template>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>
