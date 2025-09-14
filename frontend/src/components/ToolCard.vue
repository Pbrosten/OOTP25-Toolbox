<template>
  <div class="tool-card" @click="$emit('card-click')">
    <h2>{{ title }}</h2>
    <p>Search players</p>
  </div>
</template>

<script setup lang="ts">
defineProps<{
    title: string
    description: string
}>()
</script>

<style scoped>
.tool-card {
  border: 1px solid #ccc;
  padding: 1rem;
  margin-bottom: 1rem;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.tool-card:hover {
  background-color: #f5f5f5;
}
</style>