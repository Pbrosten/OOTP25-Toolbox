import { clearAdminToken, getAdminToken } from './adminToken'

export interface UpdateResult {
  status: string
  heaps_processed?: number
  long_heaps?: number
  short_heaps?: number
}

export interface Job {
  job_id: string
  status: 'pending' | 'running' | 'succeeded' | 'failed'
  result: UpdateResult | null
  error: string | null
  started_at: string
  logs: string[]
}

export interface LeagueBaseline {
  id: number
  computed_at: string
  window_start_year: number | null
  window_end_year: number | null
  lg_woba: number | null
  lg_pwoba: number | null
  ra9_baseline: number | null
  batting_pa_sample: number | null
  pitching_bf_sample: number | null
}

export interface MarketBaseline {
  id: number
  computed_at: string
  war_dollar_value: number | null
  war_dollar_value_sample: number | null
  recommendation_extend_threshold: number | null
  threshold_cohort_sample: number | null
}

export class AdminApiError extends Error {
  status: number
  body: unknown

  constructor(status: number, body: unknown) {
    const message =
      body && typeof body === 'object' && 'error' in body
        ? String((body as { error: unknown }).error)
        : `Admin API request failed (${status})`
    super(message)
    this.name = 'AdminApiError'
    this.status = status
    this.body = body
  }
}

async function adminFetch<T>(path: string, method: 'GET' | 'POST' = 'GET'): Promise<T> {
  const response = await fetch(`/api/admin${path}`, {
    method,
    headers: {
      'X-Admin-Token': getAdminToken(),
    },
  })

  const body = await response.json().catch(() => null)

  if (response.status === 401) {
    clearAdminToken()
  }

  if (!response.ok) {
    throw new AdminApiError(response.status, body)
  }

  return body as T
}

export function initDatabase(): Promise<UpdateResult> {
  return adminFetch<UpdateResult>('/init-db', 'POST')
}

export function updateDatabase(): Promise<{ job_id: string }> {
  return adminFetch<{ job_id: string }>('/update-db', 'POST')
}

export function getJob(jobId: string): Promise<Job> {
  return adminFetch<Job>(`/jobs/${encodeURIComponent(jobId)}`)
}

export function getLeagueBaselines(): Promise<LeagueBaseline[]> {
  return adminFetch<LeagueBaseline[]>('/league-baselines')
}

export function getMarketBaselines(): Promise<MarketBaseline[]> {
  return adminFetch<MarketBaseline[]>('/market-baselines')
}
