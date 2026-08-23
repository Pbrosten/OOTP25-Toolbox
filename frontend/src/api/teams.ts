export interface Team {
  team_id: number
  name: string
  abbr: string
  nickname: string
  background_color: string | null
  text_color: string | null
}

export async function fetchTeams(): Promise<Team[]> {
  const response = await fetch('/api/teams')
  if (!response.ok) {
    throw new Error('Failed to load teams.')
  }
  return response.json()
}

export interface TeamWarSummary {
  team_id: number
  war: number
  rank: number
  total_teams: number
}

export async function fetchTeamWarSummary(teamId: number): Promise<TeamWarSummary> {
  const response = await fetch(`/api/teams/${teamId}/war-summary`)
  if (!response.ok) {
    throw new Error('Failed to load team WAR summary.')
  }
  return response.json()
}
