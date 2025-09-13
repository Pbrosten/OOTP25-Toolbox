<!-- PlayerCard.vue -->
<template>
  <div class="player-card" @click="$emit('card-click')">
    <h2>{{ title }}</h2>
    <p>Click to view stats</p>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
}>()
</script>

<style scoped>
.player-card {
  border: 1px solid #ccc;
  padding: 1rem;
  margin-bottom: 1rem;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.player-card:hover {
  background-color: #f5f5f5;
}
</style>
