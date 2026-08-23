<script setup lang="ts">
import { ref, watch } from 'vue'
import { useCurrentTeam } from '@/composables/useCurrentTeam'
import { fetchTeamWarSummary } from '@/api/teams'

// GM Command Center's headline "power ranking" stat (ticket 0038/0079) --
// scoped to whichever team useCurrentTeam() currently points at, same as
// the rest of the dashboard's per-org widgets, so it re-fetches on its
// own whenever the user switches teams rather than needing a parent to
// pass a fresh prop down. Leads with the team's rank among all MLB teams
// by roster WAR (get_team_war_summary.sql), not the raw WAR number --
// per the user's explicit request, WAR itself is shown as supporting
// detail underneath.
const { currentTeamId } = useCurrentTeam()

const war = ref<number | null>(null)
const rank = ref<number | null>(null)
const totalTeams = ref<number | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

watch(currentTeamId, fetchWar, { immediate: true })

async function fetchWar() {
  if (currentTeamId.value === null) {
    loading.value = false
    war.value = null
    rank.value = null
    totalTeams.value = null
    error.value = null
    return
  }

  loading.value = true
  error.value = null

  try {
    const data = await fetchTeamWarSummary(currentTeamId.value)
    war.value = data.war
    rank.value = data.rank
    totalTeams.value = data.total_teams
  } catch (err: any) {
    error.value = err.message || 'An error occurred.'
  } finally {
    loading.value = false
  }
}

function formatWar(value: number): string {
  return value.toFixed(1)
}
</script>

<template>
  <div class="px-4 py-3 rounded bg-gray-50 inline-block">
    <div class="text-gray-500 text-sm">Power Ranking</div>
    <div v-if="loading" class="text-gray-500 text-sm">Loading...</div>
    <div v-else-if="error" class="text-red-500 text-sm">{{ error }}</div>
    <div v-else-if="rank === null" class="text-gray-500 text-sm">No team selected.</div>
    <template v-else>
      <div class="font-semibold text-2xl text-team">
        #{{ rank }}
        <span class="text-sm text-gray-400 font-normal">of {{ totalTeams }}</span>
      </div>
      <div class="text-xs text-gray-500 mt-1">{{ formatWar(war!) }} WAR</div>
    </template>
  </div>
</template>
