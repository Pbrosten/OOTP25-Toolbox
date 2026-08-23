<script setup lang="ts">
import { useCurrentTeam } from '@/composables/useCurrentTeam'
import TeamWarWidget from '@/components/dashboard/TeamWarWidget.vue'
import RosterWeaknessesWidget from '@/components/dashboard/RosterWeaknessesWidget.vue'
import ContractDecisionsWidget from '@/components/dashboard/ContractDecisionsWidget.vue'
import PromotionReadyWidget from '@/components/dashboard/PromotionReadyWidget.vue'

// GM Command Center dashboard shell (ticket 0085), replacing the old
// ToolCard launcher -- Sidebar.vue already carries tool nav (ticket 0065),
// so a separate launcher page here was redundant. Built incrementally
// (per the user, 2026-08-23) as each of 0079-0084's widgets lands, rather
// than waiting for all of them -- this page doubles as the visual
// confirmation surface for those tickets while they're in progress.
const { currentTeam } = useCurrentTeam()
</script>

<template>
  <div class="p-6 max-w-5xl mx-auto">
    <!-- No org selected (ticket 0085's outstanding design question,
         resolved 2026-08-23): direct to /gm rather than falling back to
         the old tool launcher -- Sidebar.vue already covers that nav. -->
    <div v-if="!currentTeam" class="max-w-md mx-auto mt-16 text-center">
      <h1 class="text-xl font-semibold mb-2">No organization selected</h1>
      <p class="text-gray-600 mb-4">
        Pick your org to see its GM Command Center dashboard.
      </p>
      <router-link
        to="/gm"
        class="inline-block px-4 py-2 text-sm font-medium rounded-md bg-team text-team-on-bg hover:opacity-90"
      >
        Select Organization
      </router-link>
    </div>

    <template v-else>
      <!-- Header/summary strip: 0079's team WAR headline stat. -->
      <div class="flex items-center justify-between mb-6">
        <h1 class="text-2xl font-semibold">
          {{ currentTeam.name }} {{ currentTeam.nickname }}
        </h1>
        <TeamWarWidget />
      </div>

      <!-- Widget grid: 0080's tile drops in here as it closes.
           RosterWeaknessesWidget/ContractDecisionsWidget render
           full-width instead (each has its own internal multi-item list
           layout that doesn't fit a compact stat-tile grid cell). -->
      <section class="mb-8">
        <h2 class="text-sm font-semibold uppercase tracking-wide text-gray-400 mb-3">
          Roster Insights
        </h2>
        <RosterWeaknessesWidget class="mb-4" />
        <ContractDecisionsWidget class="mb-4" />
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <p class="text-sm text-gray-400 italic">More widgets land here as 0080 closes.</p>
        </div>
      </section>

      <!-- Prospect Watch: 0083's promotion-ready prospects. -->
      <section class="mb-8">
        <h2 class="text-sm font-semibold uppercase tracking-wide text-gray-400 mb-3">
          Prospect Watch
        </h2>
        <PromotionReadyWidget />
      </section>

      <!-- Action Queue (ticket 0084). -->
      <section>
        <h2 class="text-sm font-semibold uppercase tracking-wide text-gray-400 mb-3">
          Action Queue
        </h2>
        <p class="text-sm text-gray-400 italic">Lands with ticket 0084.</p>
      </section>
    </template>
  </div>
</template>
