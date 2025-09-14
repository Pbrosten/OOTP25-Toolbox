<template>
  <div>
    <PlayerDetails :playerId="playerId" />
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import PlayerDetails from '@/components/PlayerDetails.vue'

const route = useRoute()
const playerId = Number(route.params.id)
</script>