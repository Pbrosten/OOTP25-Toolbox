<template>
  <aside
    class="shrink-0 border-r border-gray-200 bg-gray-50 py-6 flex flex-col transition-[width] duration-150"
    :class="collapsed ? 'w-16 px-2' : 'w-56 px-3'"
  >
    <button
      type="button"
      class="flex items-center justify-center w-8 h-8 mb-4 self-end rounded-md text-gray-400 hover:bg-white hover:text-team"
      :title="collapsed ? 'Expand sidebar' : 'Collapse sidebar'"
      @click="collapsed = !collapsed"
    >
      <ChevronDoubleRightIcon v-if="collapsed" class="w-4 h-4" />
      <ChevronDoubleLeftIcon v-else class="w-4 h-4" />
    </button>

    <router-link
      to="/"
      class="flex items-center gap-3 px-3 py-2 mb-4 rounded-md text-sm font-medium text-gray-600 transition-colors hover:bg-white hover:text-team hover:shadow-sm"
      active-class="bg-team-subtle text-team hover:bg-team-subtle"
      :title="collapsed ? 'Home' : undefined"
    >
      <HomeIcon class="w-5 h-5 shrink-0" />
      <span v-if="!collapsed">Home</span>
    </router-link>

    <p v-if="!collapsed" class="px-3 mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
      Tools
    </p>
    <nav class="flex flex-col gap-1">
      <router-link
        v-for="link in links"
        :key="link.to"
        :to="link.to"
        class="flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium text-gray-600 transition-colors hover:bg-white hover:text-team hover:shadow-sm"
        active-class="bg-team-subtle text-team hover:bg-team-subtle"
        :title="collapsed ? link.label : undefined"
      >
        <component :is="link.icon" class="w-5 h-5 shrink-0" />
        <span v-if="!collapsed">{{ link.label }}</span>
      </router-link>
    </nav>

    <router-link
      to="/gm"
      class="mt-auto flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium text-gray-600 transition-colors hover:bg-white hover:text-team hover:shadow-sm"
      active-class="bg-team-subtle text-team hover:bg-team-subtle"
      :title="collapsed ? 'GM' : undefined"
    >
      <Cog6ToothIcon class="w-5 h-5 shrink-0" />
      <span v-if="!collapsed">GM</span>
    </router-link>
  </aside>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import {
  HomeIcon,
  MagnifyingGlassIcon,
  UserGroupIcon,
  RocketLaunchIcon,
  Cog6ToothIcon,
  ChevronDoubleLeftIcon,
  ChevronDoubleRightIcon,
} from '@heroicons/vue/24/outline'

const collapsed = ref(false)

const links = [
  { to: '/search', label: 'Find a Player', icon: MagnifyingGlassIcon },
  { to: '/teams', label: 'Depth Chart', icon: UserGroupIcon },
  { to: '/prospects', label: 'Prospect Pipelines', icon: RocketLaunchIcon },
]
</script>
