<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  Combobox,
  ComboboxInput,
  ComboboxOptions,
  ComboboxOption
} from '@headlessui/vue'

const searchQuery = ref('')
const filteredResults = ref([])
const selectedPlayer = ref(null)
const router = useRouter()

const handleSearch = async (event) => {
  searchQuery.value = event.target.value

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

const goToPlayer = (player) => {
  console.log('Selected player:', player)
  if (player?.player_id) {
    router.push(`/players/${player.player_id}`)
  }
}

const handleEnter = () => {
  if (filteredResults.value.length === 1) {
    goToPlayer(filteredResults.value[0])
  }
}

const onPlayerSelect = (player) => {
  selectedPlayer.value = player
  goToPlayer(player)
}
</script>

<template>
  <div class="max-w-xl mx-auto p-6">
    <h1 class="text-2xl font-semibold mb-4">Search</h1>

    <Combobox :modelValue="selectedPlayer" @update:modelValue="onPlayerSelect">
      <div class="relative">
        <ComboboxInput
          class="w-full border border-gray-300 rounded-md py-2 px-4 focus:outline-none focus:ring-2 focus:ring-white focus:border-team"
          placeholder="Search for a player..."
          @input="handleSearch"
          :display-value="(player) => player ? player.first_name + ' ' + player.last_name : searchQuery"
        />

        <ComboboxOptions
          v-if="filteredResults.length"
          class="absolute mt-1 max-h-60 w-full overflow-auto rounded-md bg-white py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm z-50"
        >
          <ComboboxOption
            v-for="result in filteredResults"
            :key="result.player_id"
            :value="result"
            as="template"
          >
            <template #default="{ active, selected }">
              <li
                class="relative cursor-pointer select-none py-2 pl-10 pr-4"
                :class="{
                  'bg-blue-500 text-white': active,
                  'font-semibold': selected,
                  'text-gray-900': !active
                }"
              >
                <span class="block truncate">
                  {{ result.first_name }} {{ result.last_name }} | {{ result.position }} | {{ result.team_abbr }}
                </span>
              </li>
            </template>
          </ComboboxOption>
        </ComboboxOptions>
      </div>
    </Combobox>

    <div v-if="!filteredResults.length && searchQuery" class="mt-4 text-gray-500">
      No results found.
    </div>
  </div>
</template>
