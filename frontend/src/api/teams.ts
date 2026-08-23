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

export type RosterStrengthClassification = 'weakness' | 'surplus' | 'neutral'

export interface RosterStrengthPlayer {
  player_id: number
  first_name: string
  last_name: string
  league_rank: number
}

export interface RosterStrengthSurplusPlayer extends RosterStrengthPlayer {
  war: number
}

export interface RosterStrengthGroup {
  group: string
  classification: RosterStrengthClassification
  best_war: number | null
  best_percentile: number | null
  best_player: RosterStrengthPlayer | null
  league_pool_size: number
  surplus_count: number
  surplus_players: RosterStrengthSurplusPlayer[]
}

export interface RosterStrength {
  team_id: number
  groups: RosterStrengthGroup[]
}

export async function fetchTeamRosterStrength(teamId: number): Promise<RosterStrength> {
  const response = await fetch(`/api/teams/${teamId}/roster-strength`)
  if (!response.ok) {
    throw new Error('Failed to load team roster strength.')
  }
  return response.json()
}
