export interface ProspectValue {
  available: boolean
  fv: number | null
  mlb_promotion_ready?: boolean
}

export interface Prospect {
  player_id: number
  first_name: string
  last_name: string
  position: string
  level: number
  team_abbr: string
  value: ProspectValue
}

// team_id scopes to the given MLB team plus every affiliate whose
// parent_team_id points at it (GET /api/prospects's own docstring) --
// exactly the "whole org's farm system" scope the promotion-ready widget
// needs (ticket 0083).
export async function fetchTeamProspects(teamId: number): Promise<Prospect[]> {
  const response = await fetch(`/api/prospects?team_id=${teamId}`)
  if (!response.ok) {
    throw new Error('Failed to load prospects.')
  }
  return response.json()
}
