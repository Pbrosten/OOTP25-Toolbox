<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import PlayerDetails from '@/components/PlayerDetails.vue'
import BatterPercentiles from '@/components/percentiles/BatterPercentiles'

const route = useRoute()
const playerId = Number(route.params.id)

const playerDetailsRef = ref<InstanceType<typeof PlayerDetails> | null>(null)

watch(
  () => playerDetailsRef.value?.playerDetails,
  (details) => {
    if (details?.position === 'P') {
      console.log('Pitcher detected in parent view!')
    }
  }
)
</script>

<template>
  <div>
    <PlayerDetails ref="playerDetailsRef" :playerId="playerId" />
    <PitcherPercentiles v-if="playerDetailsRef.position === 'P'" :playerId="playerId"/>
    <BatterPercentiles v-else :playerId="playerId"/>
  </div>
</template>
