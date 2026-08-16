<script setup lang="ts">
import { computed } from 'vue'
import { useCurrentTeam } from '@/composables/useCurrentTeam'

const { teams, currentTeamId, currentTeam, setCurrentTeam } = useCurrentTeam()

function onSelect(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  setCurrentTeam(value ? Number(value) : null)
}

const swatch = computed(() => currentTeam.value?.background_color || '#9ca3af')
</script>

<template>
  <div class="max-w-xl mx-auto p-6">
    <h1 class="text-2xl font-semibold mb-1">GM Settings</h1>
    <p class="text-gray-600 mb-6">App-wide configuration for your GM session.</p>

    <div class="bg-white rounded-lg border border-gray-200 divide-y divide-gray-200">
      <div class="flex items-center justify-between gap-4 px-4 py-4">
        <div>
          <label for="org-select" class="block font-medium">My Organization</label>
          <p class="text-sm text-gray-500">
            Themes the app header and accents to match your org's colors.
          </p>
        </div>
        <div class="flex items-center gap-2">
          <span
            class="inline-block w-4 h-4 rounded-full border border-gray-300 shrink-0"
            :style="{ backgroundColor: swatch }"
          />
          <select
            id="org-select"
            :value="currentTeamId ?? ''"
            class="border border-gray-300 rounded-md py-2 px-3 focus:outline-none focus:ring-2 focus:ring-white focus:border-team"
            @change="onSelect"
          >
            <option value="">None selected</option>
            <option v-for="team in teams" :key="team.team_id" :value="team.team_id">
              {{ team.name }} {{ team.nickname }}
            </option>
          </select>
        </div>
      </div>
    </div>
  </div>
</template>
