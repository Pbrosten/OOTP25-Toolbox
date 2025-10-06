
<script setup>
import { useRouter } from 'vue-router'
import ToolCard from '@/components/ToolCard.vue'

const router = useRouter()

const tools = [
  {
    title: 'Player Search',
    description: 'Find a player',
    route: '/search'
  }
]

function navigateTo(route) {
  router.push(route)
}
</script>

<template>
  <div class="bg-slate-50 font-sans">
    <main class="flex justify-center items-start gap-8 mt-12 flex-wrap">
      <ToolCard
        v-for="tool in tools"
        :key="tool.title"
        :title="tool.title"
        :description="tool.description"
        @click="navigateTo(tool.route)"
      />
    </main>
  </div>
</template>