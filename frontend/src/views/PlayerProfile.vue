<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import PlayerDetails from '@/components/PlayerDetails.vue'
import BatterPercentiles from '@/components/percentiles/BatterPercentiles.vue'
//import PitcherPercentiles from '@/components/percentiles/PitcherPercentiles.vue' // uncomment when available

const route = useRoute()
const playerId = Number(route.params.id)

const playerDetailsRef = ref<InstanceType<typeof PlayerDetails> | null>(null)

const playerDetails = computed(() => playerDetailsRef.value?.playerDetails ?? null)
const position = computed(() => playerDetails.value?.position ?? null)
const leagueId = computed(() => playerDetails.value?.league_id ?? null)

const PitcherPercentiles = {}
</script>

<template>
  <div class="max-w-[1400px] mx-auto p-4">
    <div
      class="flex gap-4 items-center
             md:flex-row flex-col"
    >
      <PlayerDetails
        ref="playerDetailsRef"
        :playerId="playerId"
        class="flex-1 max-w-[50%] md:max-w-[50%] w-full"
      />

      <template v-if="playerDetails">
        <template v-if="position === 'P'">
          <PitcherPercentiles :playerId="playerId" />
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
