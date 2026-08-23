<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useCurrentTeam } from '@/composables/useCurrentTeam'
import { useActionQueue } from '@/composables/useActionQueue'
import {
  fetchTeamContractDecisions,
  type ContractDecisionPlayer,
  type ContractRecommendation,
} from '@/api/teams'

// GM Command Center's contract & arbitration decisions widget (ticket
// 0082) -- scoped to whichever team useCurrentTeam() currently points
// at, same pattern as TeamWarWidget.vue/RosterWeaknessesWidget.vue
// (tickets 0079/0081). Only players the backend already filtered to a
// live recommendation are ever present -- see
// get_team_contract_decisions's docstring.
const { currentTeamId } = useCurrentTeam()
const { setAlerts } = useActionQueue()

const players = ref<ContractDecisionPlayer[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

watch(currentTeamId, fetchDecisions, { immediate: true })

async function fetchDecisions() {
  setAlerts('contract-decisions', [])

  if (currentTeamId.value === null) {
    loading.value = false
    players.value = []
    error.value = null
    return
  }

  loading.value = true
  error.value = null

  try {
    const data = await fetchTeamContractDecisions(currentTeamId.value)
    players.value = data.players
    // Action Queue (ticket 0084): every returned player is already a
    // live decision (the backend only returns players with a real
    // recommendation), so all of them are alert-worthy.
    setAlerts(
      'contract-decisions',
      players.value.map((p) => ({
        category: 'Contract',
        message: `${playerName(p)}: ${p.recommendation}`,
        link: `/players/${p.player_id}`,
      })),
    )
  } catch (err: any) {
    error.value = err.message || 'An error occurred.'
  } finally {
    loading.value = false
  }
}

// Same order/coloring as SurplusValue.vue's recommendationClass (ticket
// 0058) -- "good news" (worth keeping/extending) down to "cut him loose
// now," so the widget reads best-to-worst top to bottom.
const RECOMMENDATION_ORDER: ContractRecommendation[] = [
  'Extend',
  'Keep short-term',
  'Trade before free agency',
  'Let walk',
  'Non-tender',
]

const recommendationClass: Record<ContractRecommendation, string> = {
  Extend: 'bg-team-subtle text-team',
  'Keep short-term': 'bg-team-subtle text-team',
  'Trade before free agency': 'bg-amber-50 text-amber-900',
  'Let walk': 'bg-amber-50 text-amber-900',
  'Non-tender': 'bg-red-50 text-red-900',
}

const grouped = computed(() => {
  const groups = new Map<ContractRecommendation, ContractDecisionPlayer[]>()
  for (const rec of RECOMMENDATION_ORDER) groups.set(rec, [])
  for (const p of players.value) {
    groups.get(p.recommendation)?.push(p)
  }
  return RECOMMENDATION_ORDER.map((rec) => ({ rec, players: groups.get(rec)! })).filter(
    (g) => g.players.length > 0,
  )
})

function playerName(p: ContractDecisionPlayer): string {
  return `${p.first_name} ${p.last_name}`
}

// Whole-dollar figures at this scale are unreadable unformatted --
// compact notation ("$8.3M") matches SurplusValue.vue's formatMoney.
function formatMoney(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(value)
}
</script>

<template>
  <div class="rounded bg-gray-50 p-4">
    <div v-if="loading" class="text-gray-500 text-sm">Loading...</div>
    <div v-else-if="error" class="text-red-500 text-sm">{{ error }}</div>
    <div v-else-if="currentTeamId === null" class="text-gray-500 text-sm">No team selected.</div>
    <p v-else-if="grouped.length === 0" class="text-sm text-gray-400 italic">
      No pending contract/arbitration decisions.
    </p>

    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-for="g in grouped" :key="g.rec">
        <h3 class="text-sm font-semibold text-gray-700 mb-2">{{ g.rec }}</h3>
        <ul class="space-y-1">
          <li
            v-for="p in g.players"
            :key="p.player_id"
            class="flex items-center justify-between px-2 py-1 rounded text-sm"
            :class="recommendationClass[p.recommendation]"
          >
            <router-link :to="`/players/${p.player_id}`" class="hover:underline">
              {{ playerName(p) }}
            </router-link>
            <span class="shrink-0 ml-2">{{ formatMoney(p.total_surplus) }}</span>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>
