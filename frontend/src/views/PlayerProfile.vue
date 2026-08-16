<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { TabGroup, TabList, Tab, TabPanels, TabPanel } from '@headlessui/vue'
import PlayerDetails from '@/components/PlayerDetails.vue'
import BatterPercentiles from '@/components/percentiles/BatterPercentiles.vue'
import PitcherPercentiles from '@/components/percentiles/PitcherPercentiles.vue'
import PitchRepertoire from '@/components/PitchRepertoire.vue'

const route = useRoute()
const playerId = Number(route.params.id)

const playerDetailsRef = ref<InstanceType<typeof PlayerDetails> | null>(null)

const playerDetails = computed(() => playerDetailsRef.value?.playerDetails ?? null)
const position = computed(() => playerDetails.value?.position ?? null)
const leagueId = computed(() => playerDetails.value?.league_id ?? null)
// TWP (ticket 0067): position stays 'P' for a two-way player, but they
// have real value on both sides -- let the user tab between Batting and
// Pitching percentiles instead of only ever showing Pitcher (position's
// own value).
const isTwp = computed(() => playerDetails.value?.is_twp ?? false)
</script>

<template>
  <div class="max-w-[1400px] mx-auto p-4">
    <div
      class="flex gap-4 items-start
             md:flex-row flex-col"
    >
      <div class="flex-1 max-w-[50%] md:max-w-[50%] w-full flex flex-col gap-4">
        <PlayerDetails
          ref="playerDetailsRef"
          :playerId="playerId"
          class="w-full"
        />
      </div>

      <template v-if="playerDetails">
        <div v-if="isTwp" class="flex-1 max-w-[50%] md:max-w-[50%] w-full">
          <TabGroup>
            <TabList class="flex gap-1 border-b border-gray-200 mb-4">
              <Tab v-slot="{ selected }" as="template">
                <button
                  class="px-4 py-2 text-sm font-semibold rounded-t-md focus:outline-none transition-colors"
                  :class="selected ? 'bg-team text-team-on-bg' : 'text-gray-600 hover:bg-gray-100'"
                >
                  Batting
                </button>
              </Tab>
              <Tab v-slot="{ selected }" as="template">
                <button
                  class="px-4 py-2 text-sm font-semibold rounded-t-md focus:outline-none transition-colors"
                  :class="selected ? 'bg-team text-team-on-bg' : 'text-gray-600 hover:bg-gray-100'"
                >
                  Pitching
                </button>
              </Tab>
            </TabList>
            <TabPanels>
              <TabPanel>
                <BatterPercentiles :playerId="playerId" :leagueId="leagueId" class="w-full" />
              </TabPanel>
              <TabPanel>
                <!-- PitchRepertoire lives inside this panel, not the left
                     column (per request) -- Headless UI's TabPanel only
                     mounts the active panel's content by default, so this
                     also satisfies "only render for a TWP when the
                     Pitching tab is selected" with no extra logic. -->
                <div class="flex flex-col gap-4">
                  <PitcherPercentiles :playerId="playerId" :leagueId="leagueId" class="w-full" />
                  <PitchRepertoire :playerId="playerId" class="w-full" />
                </div>
              </TabPanel>
            </TabPanels>
          </TabGroup>
        </div>
        <template v-else-if="position === 'P'">
          <div class="flex-1 max-w-[50%] md:max-w-[50%] w-full flex flex-col gap-4">
            <PitcherPercentiles :playerId="playerId" :leagueId="leagueId" class="w-full" />
            <PitchRepertoire :playerId="playerId" class="w-full" />
          </div>
        </template>
        <template v-else>
          <BatterPercentiles
            :playerId="playerId"
            :leagueId="leagueId"
            class="flex-1 max-w-[50%] md:max-w-[50%] w-full"
          />
        </template>
      </template>

      <template v-else>
        <div>Loading player profile...</div>
      </template>
    </div>
  </div>
</template>
