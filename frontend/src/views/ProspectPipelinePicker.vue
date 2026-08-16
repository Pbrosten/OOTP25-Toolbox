<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const teams = ref([])
const loading = ref(true)
const error = ref(null)
const selectedTeamId = ref('')

onMounted(async () => {
  try {
    const response = await fetch('/api/teams')
    if (response.ok) {
      teams.value = await response.json()
    } else {
      error.value = 'Failed to load teams.'
    }
  } catch (err) {
    error.value = 'Failed to load teams.'
  } finally {
    loading.value = false
  }
})

function goToProspects() {
  if (selectedTeamId.value) {
    router.push(`/teams/${selectedTeamId.value}/prospects`)
  }
}
</script>

<template>
  <div class="max-w-xl mx-auto p-6">
    <h1 class="text-2xl font-semibold mb-4">Prospect Pipeline</h1>

    <div v-if="loading">Loading...</div>
    <div v-else-if="error" class="text-red-500">{{ error }}</div>
    <div v-else class="flex items-center gap-3">
      <select
        v-model="selectedTeamId"
        @change="goToProspects"
        class="w-full border border-gray-300 rounded-md py-2 px-4 focus:outline-none focus:ring-2 focus:ring-white focus:border-teal-500"
      >
        <option value="" disabled>Select an org...</option>
        <option v-for="team in teams" :key="team.team_id" :value="team.team_id">
          {{ team.name }} {{ team.nickname }}
        </option>
      </select>
    </div>

    <!-- League-wide leaderboard (ticket 0074/0077): a separate, unfiltered
         ranking rather than an org-scoped one, so it's a distinct link
         here rather than a select option. -->
    <div class="mt-4 text-sm">
      <router-link to="/prospects/leaderboard" class="text-teal-700 hover:underline">
        View league-wide leaderboard →
      </router-link>
    </div>
  </div>
</template>
