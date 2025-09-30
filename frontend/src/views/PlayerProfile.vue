<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import PlayerDetails from '@/components/PlayerDetails.vue'
import BatterPercentiles from '@/components/percentiles/BatterPercentiles.vue'
//import PitcherPercentiles from '@/components/percentiles/PitcherPercentiles.vue' // uncomment when available

const route = useRoute()
const playerId = Number(route.params.id)

const playerDetailsRef = ref<InstanceType<typeof PlayerDetails> | null>(null)

const position = computed(() => playerDetailsRef.value?.playerDetails?.position || null)
</script>

<template>
  <div class="page-wrapper">
    <div class="profile-container">
        <PlayerDetails ref="playerDetailsRef" :playerId="playerId" class="player-details"/>

        <!-- <template v-if="position === 'P'">
          <PitcherPercentiles :playerId="playerId" />
        </template> -->

        <template v-if="position">
          <BatterPercentiles :playerId="playerId" class="batter-percentiles"/>
        </template>

        <template v-else>
          <div>Loading player profile...</div>
        </template>
    </div>
  </div>
</template>

<style scoped>
@media (max-width: 768px) {
  .profile-container {
    flex-direction: column;
  }

  .player-details,
  .batter-percentiles {
    max-width: 100%;
    flex: 1 1 100%;
  }
}

.page-wrapper {
  max-width: 1400px;
  margin: 0 auto;
  padding: 1rem;
}

.profile-container {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
}

.player-details,
.batter-percentiles {
  flex: 1 1 50%;
  max-width: 50%;
  box-sizing: border-box;
}
</style>
