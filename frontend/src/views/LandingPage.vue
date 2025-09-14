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
        @click="navigateTo(tool.route)"
      />
    </main>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import ToolCard from '../components/ToolCard.vue'

const router = useRouter()

const tools = [
  {
    title: 'Kyle Shwarber',
    route: '/players/12'
  }
]

function navigateTo(route) {
  router.push(route)
}
</script>

<style scoped>
</style>

