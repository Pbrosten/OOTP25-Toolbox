<script setup lang="ts">
defineProps<{
  title: string
  description: string
}>()
</script>

<template>
  <div
    class="border border-gray-300 p-4 mb-4 rounded cursor-pointer transition-colors duration-200 hover:bg-gray-100"
    @click="$emit('card-click')"
  >
    <h2 class="text-lg font-semibold">{{ title }}</h2>
    <p class="text-gray-700">{{ description }}</p>
  </div>
</template>
