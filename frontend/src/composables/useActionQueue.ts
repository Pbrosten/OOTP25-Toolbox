import { reactive, computed } from 'vue'

// Shared alert registry for the GM Command Center's Action Queue
// (ticket 0084) -- a flat list grouped by category, per the resolved
// design choice (2026-08-16): no cross-widget priority/urgency scoring,
// each of 0079-0083's widgets is just responsible for exposing its own
// alert-shaped items. Module-level singleton reactive state, same
// pattern as useCurrentTeam.ts, so ActionQueue.vue doesn't need any
// prop-drilling through LandingPage.vue and sibling widgets don't need
// to know ActionQueue.vue exists at all -- each widget just calls
// setAlerts(source, [...]) whenever its own data changes; source is a
// stable per-widget key (not shown to the user) so one widget's alerts
// don't clobber another's and can be cleanly cleared/replaced on its own
// refetch (e.g. on team switch).
export interface ActionQueueAlert {
  category: string
  message: string
  link: string
}

const alertsBySource = reactive(new Map<string, ActionQueueAlert[]>())

export function useActionQueue() {
  function setAlerts(source: string, alerts: ActionQueueAlert[]) {
    alertsBySource.set(source, alerts)
  }

  const alerts = computed(() => Array.from(alertsBySource.values()).flat())

  return { setAlerts, alerts }
}
