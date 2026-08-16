<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useCurrentTeam } from '@/composables/useCurrentTeam'

const router = useRouter()
const { teams, teamsError } = useCurrentTeam()
const selectedTeamId = ref('')

function goToDepthChart() {
  if (selectedTeamId.value) {
    router.push(`/teams/${selectedTeamId.value}/depth-chart`)
  }
}
</script>

<template>
  <div class="max-w-xl mx-auto p-6">
    <h1 class="text-2xl font-semibold mb-4">Roster Depth Chart</h1>

    <div v-if="teamsError" class="text-red-500">{{ teamsError }}</div>
    <div v-else-if="!teams.length">Loading...</div>
    <div v-else class="flex items-center gap-3">
      <select
        v-model="selectedTeamId"
        @change="goToDepthChart"
        class="w-full border border-gray-300 rounded-md py-2 px-4 focus:outline-none focus:ring-2 focus:ring-white focus:border-team"
      >
        <option value="" disabled>Select a team...</option>
        <option v-for="team in teams" :key="team.team_id" :value="team.team_id">
          {{ team.name }} {{ team.nickname }}
        </option>
      </select>
    </div>
  </div>
</template>
