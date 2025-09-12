<template>
  <div
    class="bg-white p-6 rounded-lg shadow-md cursor-pointer hover:shadow-lg transition"
    @click="$emit('click')"
  >
    <div class="text-4xl mb-4">{{ icon }}</div>
    <h2 class="text-xl font-semibold mb-2">{{ title }}</h2>
    <p class="text-gray-600">{{ description }}</p>
  </div>
</template>

<script setup>
defineProps(['title', 'description', 'icon'])
</script>
