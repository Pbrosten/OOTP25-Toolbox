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
