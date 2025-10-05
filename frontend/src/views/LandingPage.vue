<template>
  <div>
    <main>
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

<script setup>
import { useRouter } from 'vue-router'
import ToolCard from '@/components/ToolCard.vue'

const router = useRouter()

const tools = [
  {
    title: 'Player Search',
    description: 'Search players',
    route: '/search'
  },
  {
    title: 'Team Analytics',
    description: 'Analyze team performance',
    route: '/team-analytics'
  }
]

function navigateTo(route) {
  router.push(route)
}
</script>

<style scoped>
div {
  background: #f8fafc;
  font-family: 'Segoe UI', Arial, sans-serif;
}

main {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  gap: 2rem;
  margin-top: 3rem;
  flex-wrap: wrap;
}
</style>

