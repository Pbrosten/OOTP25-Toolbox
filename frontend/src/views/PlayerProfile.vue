<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
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
        <PitchRepertoire
          v-if="position === 'P'"
          :playerId="playerId"
          class="w-full"
        />
      </div>

      <template v-if="playerDetails">
        <template v-if="position === 'P'">
          <PitcherPercentiles
            :playerId="playerId"
            :leagueId="leagueId"
            class="flex-1 max-w-[50%] md:max-w-[50%] w-full"
          />
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
