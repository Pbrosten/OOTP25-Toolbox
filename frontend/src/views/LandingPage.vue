<template>
  <div class="min-h-screen bg-gray-100 text-gray-800">
    <header class="bg-white shadow-md p-6">
      <h1 class="text-3xl font-bold">Toolbox Dashboard</h1>
      <p class="text-gray-500">Your central hub for analytics and reports</p>
    </header>

    <main class="p-8 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
      <ToolboxCard
        v-for="tool in tools"
        :key="tool.title"
        :title="tool.title"
        :description="tool.description"
        :icon="tool.icon"
        @click="navigateTo(tool.route)"
      />
    </main>

    <footer class="text-center p-4 text-sm text-gray-400">
      &copy; 2025 Toolbox Inc. All rights reserved.
    </footer>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import ToolboxCard from '@/components/ToolboxCard.vue'

const router = useRouter()

const tools = [
  {
    title: 'User Analytics',
    description: 'View behavior and usage patterns.',
    icon: '📊',
    route: '/analytics/users'
  },
  {
    title: 'Sales Reports',
    description: 'Track revenue and trends.',
    icon: '💰',
    route: '/reports/sales'
  },
  {
    title: 'System Logs',
    description: 'Monitor backend operations.',
    icon: '🛠️',
    route: '/logs/system'
  },
  {
    title: 'Performance Metrics',
    description: 'Analyze speed and efficiency.',
    icon: '⚡',
    route: '/metrics/performance'
  },
  {
    title: 'Data Explorer',
    description: 'Query and visualize raw data.',
    icon: '🔍',
    route: '/explorer'
  }
]

function navigateTo(route) {
  router.push(route)
}
</script>

<style scoped>
</style>

