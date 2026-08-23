<script setup lang="ts">
import { useCurrentTeam } from '@/composables/useCurrentTeam'
import TeamWarWidget from '@/components/dashboard/TeamWarWidget.vue'
import RosterWeaknessesWidget from '@/components/dashboard/RosterWeaknessesWidget.vue'
import ContractDecisionsWidget from '@/components/dashboard/ContractDecisionsWidget.vue'
import PerformanceDeltasWidget from '@/components/dashboard/PerformanceDeltasWidget.vue'
import PromotionReadyWidget from '@/components/dashboard/PromotionReadyWidget.vue'
import ActionQueue from '@/components/dashboard/ActionQueue.vue'

// GM Command Center dashboard shell (ticket 0085), replacing the old
// ToolCard launcher -- Sidebar.vue already carries tool nav (ticket 0065),
// so a separate launcher page here was redundant. Built incrementally
// (per the user, 2026-08-23) as each of 0079-0084's widgets lands, rather
// than waiting for all of them -- this page doubles as the visual
// confirmation surface for those tickets while they're in progress.
const { currentTeam } = useCurrentTeam()
</script>

<template>
  <div class="p-6 max-w-6xl mx-auto">
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

      <!-- Two-column layout (per the user, 2026-08-23): main content
           left, ActionQueue as a collapsible feed to the right -- it
           owns its own header/collapse toggle (see its own comment),
           not wrapped in a <section> here. -->
      <div class="flex flex-col lg:flex-row gap-6 items-start">
        <div class="flex-1 min-w-0">
          <!-- Roster Insights: 0080/0081/0082's widgets. Each renders
               full-width -- all three have their own internal multi-item
               list layout that doesn't fit a compact stat-tile grid cell. -->
          <section class="mb-8">
            <h2 class="text-sm font-semibold uppercase tracking-wide text-gray-400 mb-3">
              Roster Insights
            </h2>
            <RosterWeaknessesWidget class="mb-4" />
            <ContractDecisionsWidget class="mb-4" />
            <PerformanceDeltasWidget />
          </section>

          <!-- Prospect Watch: 0083's promotion-ready prospects. -->
          <section>
            <h2 class="text-sm font-semibold uppercase tracking-wide text-gray-400 mb-3">
              Prospect Watch
            </h2>
            <PromotionReadyWidget />
          </section>
        </div>

        <!-- Action Queue (ticket 0084): aggregates alerts pushed by the
             widgets to the left via useActionQueue(). -->
        <ActionQueue />
      </div>
    </template>
  </div>
</template>
