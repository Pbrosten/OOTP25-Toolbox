<script setup lang="ts">
import { ref, computed } from 'vue'
import { ChevronDoubleLeftIcon, ChevronDoubleRightIcon } from '@heroicons/vue/24/outline'
import { useActionQueue } from '@/composables/useActionQueue'

// GM Command Center's Action Queue (ticket 0084): a flat list grouped by
// category, per the resolved design choice (2026-08-16) -- no
// cross-widget priority/urgency scoring for v1. Purely a frontend
// aggregation: each of 0080-0083's widgets pushes its own alert-shaped
// items into the shared useActionQueue() registry as its data loads (see
// their own fetch functions); this component only groups and renders
// whatever's currently registered. 0079's team WAR widget contributes
// nothing -- it's just a stat, not an alert (ticket's own Approach).
//
// Renders as a collapsible right-hand feed (per the user, 2026-08-23),
// not a full-width section -- owns its own header/collapse toggle here
// (same collapse convention as Sidebar.vue) rather than LandingPage.vue
// wrapping it in a <section>, since the collapsed rail needs to control
// its own width including the header.
const { alerts } = useActionQueue()
const collapsed = ref(false)

// Roughly matches LandingPage.vue's section order (Roster Insights, then
// Prospect Watch) so the queue reads top-to-bottom the same way the
// dashboard itself does. An unrecognized category (shouldn't happen;
// defensive only) sorts last via .indexOf()'s -1 wrapping to Infinity.
const CATEGORY_ORDER = ['Roster', 'Contract', 'Performance', 'Prospects']

const grouped = computed(() => {
  const groups = new Map<string, typeof alerts.value>()
  for (const alert of alerts.value) {
    if (!groups.has(alert.category)) groups.set(alert.category, [])
    groups.get(alert.category)!.push(alert)
  }
  return Array.from(groups.entries())
    .map(([category, items]) => ({ category, items }))
    .sort((a, b) => {
      const ai = CATEGORY_ORDER.indexOf(a.category)
      const bi = CATEGORY_ORDER.indexOf(b.category)
      return (ai === -1 ? Infinity : ai) - (bi === -1 ? Infinity : bi)
    })
})
</script>

<template>
  <aside
    class="shrink-0 rounded bg-gray-50 transition-[width] duration-150"
    :class="collapsed ? 'w-12 p-2' : 'w-full lg:w-72 p-4'"
  >
    <div class="flex items-center justify-between" :class="{ 'mb-3': !collapsed }">
      <h2 v-if="!collapsed" class="text-sm font-semibold uppercase tracking-wide text-gray-400">
        Action Queue
      </h2>
      <button
        type="button"
        class="flex items-center justify-center w-7 h-7 rounded-md text-gray-400 hover:bg-white hover:text-team"
        :title="collapsed ? 'Expand Action Queue' : 'Collapse Action Queue'"
        @click="collapsed = !collapsed"
      >
        <!-- Right-docked panel: collapsed reveals leftward (expand), expanded shrinks rightward (collapse) -- mirror of Sidebar.vue's left-docked chevrons. -->
        <ChevronDoubleLeftIcon v-if="collapsed" class="w-4 h-4" />
        <ChevronDoubleRightIcon v-else class="w-4 h-4" />
      </button>
    </div>

    <div
      v-if="collapsed && alerts.length > 0"
      class="mt-2 flex justify-center"
      :title="`${alerts.length} item(s) need your attention`"
    >
      <span class="w-6 h-6 flex items-center justify-center rounded-full bg-team text-team-on-bg text-xs font-semibold">
        {{ alerts.length }}
      </span>
    </div>

    <template v-else-if="!collapsed">
      <p v-if="grouped.length === 0" class="text-sm text-gray-400 italic">
        Nothing needs your attention right now.
      </p>

      <div v-else class="space-y-4">
        <div v-for="g in grouped" :key="g.category">
          <h3 class="text-sm font-semibold text-gray-700 mb-2">{{ g.category }}</h3>
          <ul class="space-y-1">
            <li
              v-for="(item, i) in g.items"
              :key="i"
              class="px-2 py-1 rounded bg-white border border-gray-100 text-sm"
            >
              <router-link :to="item.link" class="hover:underline hover:text-team">
                {{ item.message }}
              </router-link>
            </li>
          </ul>
        </div>
      </div>
    </template>
  </aside>
</template>
