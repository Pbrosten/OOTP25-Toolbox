<template>
  <div class="search-landing-page">
    <h1>Search</h1>
    <input
      v-model="searchQuery"
      @input="handleSearch"
      type="text"
      placeholder="Search for something..."
    />

    <div v-if="filteredResults.length">
      <h2>Results:</h2>
      <ul>
        <li v-for="result in filteredResults" :key="result.id">
          <router-link
            :to="`/players/${result.player_id}`"
            class="player-button"
          >
            {{ result.first_name }} {{ result.last_name }} | {{ result.position }} | {{ result.team_abbr }}
          </router-link>
        </li>
      </ul>
    </div>
    <p v-else-if="searchQuery">No results found.</p>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const searchQuery = ref('')
const filteredResults = ref([])

const handleSearch = async () => {
  if (!searchQuery.value) {
    filteredResults.value = []
    return
  }
  try {
    const response = await fetch(`/api/players/search?q=${encodeURIComponent(searchQuery.value)}`)
    if (response.ok) {
      filteredResults.value = await response.json()
    } else {
      filteredResults.value = []
    }
  } catch (err) {
    filteredResults.value = []
  }
}
</script>

<!-- <style scoped>
.search-landing-page {
  max-width: 600px;
  margin: auto;
  padding: 2rem;
}

input[type="text"] {
  width: 100%;
  padding: 0.5rem;
  margin-bottom: 1rem;
  font-size: 1rem;
}
</style> -->
