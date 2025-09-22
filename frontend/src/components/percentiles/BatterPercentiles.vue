<script lang="ts">
import { ref, onMounted } from 'vue'

const props = defineProps<{ playerId: number }>()

const playerRating = ref<any>(null)
const xStatsBat = ref<any>(null)
const xStatsRun = ref<any>(null)
const xStatsField = ref<any>(null)

const loading = ref(true)
const error = ref<string | null>(null)

onMounted(async () => {
    loading.value = true
    error.value = null
    try {
        // Fetch most recent player rating id
        const ratingRes = await fetch(`/api/players/${props.playerId}/ratings?latest=true`)
        if (ratingRes.ok) {
            playerRating.value = await ratingRes.json()
        } else {
            error.value = 'Failed to load player rating info.'
        }
        // Fetch expected batting stats
        const batRes = await fetch(`/api/players/stats/expected/expected/batting/${playerRating.rating_id}`)
        if (batRes.ok) {
            xStatsBat.value = await batRes.json()
        } else {
            error.value = 'Failed to load expected batting stats.'
        }
        // Fetch expected batting stats
        const runRes = await fetch(`/api/players/stats/expected/expected/basepath/${playerRating.rating_id}`)
        if (batRes.ok) {
            xStatsRun.value = await runRes.json()
        } else {
            error.value = 'Failed to load expected basepath stats.'
        }
        // Fetch expected batting stats
        const fieldRes = await fetch(`/api/players/stats/expected/expected/fielding/${playerRating.rating_id}`)
        if (batRes.ok) {
            xStatsField.value = await fieldRes.json()
        } else {
            error.value = 'Failed to load expected fielding stats.'
        }
    }
})
</script>

// Process for touching DB
// 1. find most recent rating id by player id
// 2. pull expected batting stats by rating id
// 3. pull expected basepah stats by rating id
// 4. pull expected fielding stats by rating id
// 5. format data and visualize