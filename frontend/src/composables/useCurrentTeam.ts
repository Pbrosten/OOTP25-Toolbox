import { computed, ref } from 'vue'
import { fetchTeams, type Team } from '@/api/teams'

const STORAGE_KEY = 'ootp-toolbox:current-team-id'

const DEFAULT_BG = '#115e59' // teal-800, matches the app's pre-theming default chrome
const DEFAULT_TEXT = '#ffffff'

const teams = ref<Team[]>([])
const teamsLoaded = ref(false)
const teamsError = ref<string | null>(null)
const currentTeamId = ref<number | null>(readStoredTeamId())

function readStoredTeamId(): number | null {
  const stored = localStorage.getItem(STORAGE_KEY)
  return stored ? Number(stored) : null
}

async function ensureTeamsLoaded() {
  if (teamsLoaded.value) return
  try {
    teams.value = await fetchTeams()
  } catch {
    teamsError.value = 'Failed to load teams.'
  } finally {
    teamsLoaded.value = true
  }
}

const currentTeam = computed<Team | null>(
  () => teams.value.find((t) => t.team_id === currentTeamId.value) || null,
)

const teamColors = computed(() => ({
  '--team-bg': currentTeam.value?.background_color || DEFAULT_BG,
  '--team-text': currentTeam.value?.text_color || DEFAULT_TEXT,
}))

function setCurrentTeam(teamId: number | null) {
  currentTeamId.value = teamId
  if (teamId === null) {
    localStorage.removeItem(STORAGE_KEY)
  } else {
    localStorage.setItem(STORAGE_KEY, String(teamId))
  }
}

export function useCurrentTeam() {
  ensureTeamsLoaded()
  return { teams, teamsError, currentTeamId, currentTeam, teamColors, setCurrentTeam }
}
