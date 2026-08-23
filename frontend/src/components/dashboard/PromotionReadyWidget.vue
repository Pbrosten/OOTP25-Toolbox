<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { ArrowUpCircleIcon } from '@heroicons/vue/20/solid'
import { useCurrentTeam } from '@/composables/useCurrentTeam'
import { useActionQueue } from '@/composables/useActionQueue'
import { fetchTeamProspects, type Prospect } from '@/api/prospects'

// GM Command Center's prospect promotion opportunities widget (ticket
// 0083) -- scoped to whichever team useCurrentTeam() currently points
// at, same pattern as the other dashboard widgets. Frontend-only:
// reuses GET /api/prospects's existing mlb_promotion_ready flag (ticket
// 0068/0069) as-is, no new backend work needed.
const { currentTeamId } = useCurrentTeam()
const { setAlerts } = useActionQueue()

const prospects = ref<Prospect[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

watch(currentTeamId, fetchProspects, { immediate: true })

async function fetchProspects() {
  if (currentTeamId.value === null) {
    loading.value = false
    prospects.value = []
    error.value = null
    return
  }

  loading.value = true
  error.value = null

  try {
    prospects.value = await fetchTeamProspects(currentTeamId.value)
  } catch (err: any) {
    error.value = err.message || 'An error occurred.'
  } finally {
    loading.value = false
  }
}

// mlb_promotion_ready is only present at level != 1 (MLB) -- see GET
// /api/prospects's docstring -- so filtering on it alone already
// excludes the team's actual MLB roster, no separate level check needed.
const promotionReady = computed(() =>
  prospects.value
    .filter((p) => p.value.available && p.value.mlb_promotion_ready)
    .sort((a, b) => (b.value.fv ?? 0) - (a.value.fv ?? 0)),
)

// Action Queue (ticket 0084): every promotion-ready prospect is
// alert-worthy -- watching the derived list (not re-filtering inside
// fetchProspects) keeps this in sync with promotionReady without
// duplicating its filter/sort logic, and naturally clears to [] when
// prospects.value does (no team selected).
watch(
  promotionReady,
  (list) => {
    setAlerts(
      'promotion-ready',
      list.map((p) => ({
        category: 'Prospects',
        message: `${playerName(p)} (${p.position}) is ready for MLB promotion`,
        link: `/players/${p.player_id}`,
      })),
    )
  },
  { immediate: true },
)

const LEVEL_LABELS: Record<number, string> = {
  2: 'AAA',
  3: 'AA',
  4: 'A / High-A',
  6: 'Rookie / Complex',
}

function playerName(p: Prospect): string {
  return `${p.first_name} ${p.last_name}`
}

// Same FV tiering as ProspectPipeline.vue's fvClass (ticket 0070) -- no
// "bad" tier, even a replacement-level-ceiling prospect is a real asset.
function fvClass(fv: number | null): string {
  if (fv === null) return 'bg-gray-100 text-gray-800'
  if (fv >= 55) return 'bg-team-subtle text-team'
  if (fv >= 45) return 'bg-gray-100 text-gray-800'
  return 'bg-amber-50 text-amber-900'
}
</script>

<template>
  <div class="rounded bg-gray-50 p-4">
    <div v-if="loading" class="text-gray-500 text-sm">Loading...</div>
    <div v-else-if="error" class="text-red-500 text-sm">{{ error }}</div>
    <div v-else-if="currentTeamId === null" class="text-gray-500 text-sm">No team selected.</div>
    <p v-else-if="promotionReady.length === 0" class="text-sm text-gray-400 italic">
      No prospects ready for promotion right now.
    </p>

    <ul v-else class="space-y-1">
      <li
        v-for="p in promotionReady"
        :key="p.player_id"
        class="flex items-center justify-between px-2 py-1 rounded bg-white border border-gray-100 text-sm"
      >
        <span>
          <router-link :to="`/players/${p.player_id}`" class="hover:underline font-medium">
            {{ playerName(p) }}
          </router-link>
          <ArrowUpCircleIcon
            class="inline-block h-4 w-4 text-team align-text-bottom ml-1"
            title="MLB promotion ready: current-form projection already grades as a bench player/backend starter or better"
          />
          <span class="text-xs text-gray-400 ml-1">
            {{ p.position }} · {{ LEVEL_LABELS[p.level] || p.level }} · {{ p.team_abbr }}
          </span>
        </span>
        <span
          class="shrink-0 ml-2 px-2 py-0.5 rounded-full text-xs font-semibold"
          :class="fvClass(p.value.fv)"
        >
          {{ p.value.fv }}
        </span>
      </li>
    </ul>
  </div>
</template>
