<script setup lang="ts">
import Header from '@/components/Header.vue'
import Sidebar from '@/components/Sidebar.vue'
import { useCurrentTeam } from '@/composables/useCurrentTeam'

const { teamColors } = useCurrentTeam()
</script>

<template>
  <div class="h-screen flex flex-col" :style="teamColors">
    <Header />
    <div class="flex flex-1 min-h-0">
      <Sidebar />
      <main class="flex-1 min-w-0 overflow-y-auto">
        <router-view :key="$route.fullPath" />
      </main>
    </div>
  </div>
</template>