<template>
  <div>
    <header>
      <h1>Toolbox Dashboard</h1>
      <p>Your central hub for analytics and reports</p>
    </header>

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

header {
  text-align: center;
  padding: 2rem 0 1rem 0;
  background: var(--color-primary);
  color: var(--color-tertiary);
  border-radius: 0 0 16px 16px;
  box-shadow: 0 2px 8px rgba(30,41,59,0.08);
}

header h1 {
  margin: 0;
  font-size: 2.5rem;
  letter-spacing: 1px;
}

header p {
  margin: 0.5rem 0 0 0;
  font-size: 1.2rem;
  color: #cbd5e1;
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

