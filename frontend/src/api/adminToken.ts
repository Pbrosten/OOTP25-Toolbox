const STORAGE_KEY = 'ootp_admin_token'

/**
 * Returns the admin API token, prompting the user for it and caching the
 * result in sessionStorage if none is stored yet. Cleared per tab/session --
 * never baked into the build or committed to source.
 */
export function getAdminToken(): string {
  const stored = sessionStorage.getItem(STORAGE_KEY)
  if (stored) {
    return stored
  }

  const entered = window.prompt('Enter the admin API token (X-Admin-Token):') ?? ''
  if (entered) {
    sessionStorage.setItem(STORAGE_KEY, entered)
  }
  return entered
}

/** Drops the cached token, e.g. after a 401, so the next call re-prompts. */
export function clearAdminToken(): void {
  sessionStorage.removeItem(STORAGE_KEY)
}
