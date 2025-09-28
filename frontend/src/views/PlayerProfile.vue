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
  <div>
    <PlayerDetails ref="playerDetailsRef" :playerId="playerId" />

    <!-- <PitcherPercentiles
      v-if="position === 'P'"
      :playerId="playerId"
    /> -->
    
    <BatterPercentiles
      v-if="position"
      :playerId="playerId"
    />
    
    <div v-else>
      Loading player profile...
    </div>
  </div>
</template>
