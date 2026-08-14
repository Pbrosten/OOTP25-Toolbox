<script setup lang="ts">
import { ref, onMounted } from 'vue'

const props = defineProps<{ playerId: number }>()

interface PitchRepertoireEntry {
  rating_id: number
  pitch_type: string
  grade: number
  talent_grade: number
}

// Matches the source export's column-suffix spelling exactly (e.g.
// "circlechange", not "circle change") -- see ticket 0031's Design choices.
const pitchTypeLabels: Record<string, string> = {
  fastball: 'Fastball',
  slider: 'Slider',
  curveball: 'Curveball',
  screwball: 'Screwball',
  forkball: 'Forkball',
  changeup: 'Changeup',
  sinker: 'Sinker',
  splitter: 'Splitter',
  knuckleball: 'Knuckleball',
  cutter: 'Cutter',
  circlechange: 'Circle Change',
  knucklecurve: 'Knuckle Curve',
}

const repertoire = ref<PitchRepertoireEntry[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

onMounted(fetchRepertoire)

function getPitchLabel(pitchType: string): string {
  return pitchTypeLabels[pitchType] || pitchType
}

async function fetchRepertoire() {
  loading.value = true
  error.value = null

  try {
    const ratingRes = await fetch(`/api/players/${props.playerId}/ratings?latest=true`)
    if (!ratingRes.ok) throw new Error('Failed to load player rating info.')
    const ratingData = await ratingRes.json()

    const repertoireRes = await fetch(`/api/players/ratings/${ratingData.rating_id}/pitch_repertoire`)
    if (!repertoireRes.ok) throw new Error('Failed to load pitch repertoire.')
    const rows: PitchRepertoireEntry[] = await repertoireRes.json()

    repertoire.value = [...rows].sort((a, b) => b.grade - a.grade)
  } catch (err: any) {
    error.value = err.message || 'An error occurred.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="pitch-repertoire-wrapper">
    <h2 class="text-lg font-semibold mb-2">Pitch Repertoire</h2>
    <div v-if="loading">Loading...</div>
    <div v-else-if="error">{{ error }}</div>
    <div v-else-if="repertoire.length === 0">No repertoire data available.</div>
    <table v-else class="w-full max-w-md table-auto border-collapse text-sm">
      <thead>
        <tr class="bg-gray-200 text-gray-700">
          <th class="px-2 py-1 text-left">Pitch</th>
          <th class="px-2 py-1">Grade</th>
          <th class="px-2 py-1">Potential</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="entry in repertoire" :key="entry.pitch_type" class="even:bg-gray-50">
          <td class="px-2 py-1 text-left">{{ getPitchLabel(entry.pitch_type) }}</td>
          <td class="px-2 py-1 text-center">{{ entry.grade }}</td>
          <td class="px-2 py-1 text-center">{{ entry.talent_grade }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.pitch-repertoire-wrapper {
  width: 100%;
}
</style>
