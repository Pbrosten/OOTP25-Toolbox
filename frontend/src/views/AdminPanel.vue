<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  AdminApiError,
  getJob,
  getLeagueBaselines,
  getMarketBaselines,
  initDatabase,
  updateDatabase,
} from '@/api/admin'
import type { Job, LeagueBaseline, MarketBaseline } from '@/api/admin'

const POLL_INTERVAL_MS = 2000

const initStatus = ref<'idle' | 'loading' | 'done' | 'error'>('idle')
const initResult = ref<unknown>(null)
const initError = ref<string | null>(null)

const baselines = ref<LeagueBaseline[]>([])
const baselinesError = ref<string | null>(null)

async function loadLeagueBaselines() {
  baselinesError.value = null
  try {
    baselines.value = await getLeagueBaselines()
  } catch (err) {
    baselinesError.value = err instanceof AdminApiError ? err.message : 'Failed to load league baselines'
  }
}

const marketBaselines = ref<MarketBaseline[]>([])
const marketBaselinesError = ref<string | null>(null)

async function loadMarketBaselines() {
  marketBaselinesError.value = null
  try {
    marketBaselines.value = await getMarketBaselines()
  } catch (err) {
    marketBaselinesError.value = err instanceof AdminApiError ? err.message : 'Failed to load market baselines'
  }
}

function formatNumber(value: number | null, digits: number): string {
  return value === null ? '—' : value.toFixed(digits)
}

function formatDollars(value: number | null): string {
  return value === null ? '—' : `$${Math.round(value).toLocaleString()}`
}

onMounted(loadLeagueBaselines)
onMounted(loadMarketBaselines)

const job = ref<Job | null>(null)
const updateError = ref<string | null>(null)
const logContainer = ref<HTMLElement | null>(null)
let pollHandle: ReturnType<typeof setInterval> | null = null

const isUpdateRunning = computed(
  () => job.value !== null && (job.value.status === 'pending' || job.value.status === 'running'),
)

function stopPolling() {
  if (pollHandle !== null) {
    clearInterval(pollHandle)
    pollHandle = null
  }
}

function trackJob(jobId: string) {
  stopPolling()
  job.value = {
    job_id: jobId,
    status: 'pending',
    result: null,
    error: null,
    started_at: new Date().toISOString(),
    logs: [],
  }
  pollHandle = setInterval(() => pollJob(jobId), POLL_INTERVAL_MS)
  pollJob(jobId)
}

async function pollJob(jobId: string) {
  try {
    job.value = await getJob(jobId)
    if (job.value.status === 'succeeded' || job.value.status === 'failed') {
      stopPolling()
      if (job.value.status === 'succeeded') {
        loadLeagueBaselines()
        loadMarketBaselines()
      }
    }
    await nextTick()
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  } catch (err) {
    updateError.value = err instanceof AdminApiError ? err.message : 'Failed to fetch job status'
    stopPolling()
  }
}

async function handleInit() {
  if (!window.confirm('This drops and recreates the entire database schema. Continue?')) {
    return
  }
  initStatus.value = 'loading'
  initError.value = null
  try {
    initResult.value = await initDatabase()
    initStatus.value = 'done'
  } catch (err) {
    initError.value = err instanceof AdminApiError ? err.message : 'Failed to initialize database'
    initStatus.value = 'error'
  }
}

async function handleUpdate() {
  updateError.value = null
  try {
    const { job_id } = await updateDatabase()
    trackJob(job_id)
  } catch (err) {
    if (err instanceof AdminApiError && err.status === 409 && isJobIdBody(err.body)) {
      trackJob(err.body.job_id)
      return
    }
    updateError.value = err instanceof AdminApiError ? err.message : 'Failed to start update'
  }
}

function isJobIdBody(body: unknown): body is { job_id: string } {
  return typeof body === 'object' && body !== null && 'job_id' in body
}

onBeforeUnmount(stopPolling)
</script>

<template>
  <div class="max-w-2xl mx-auto p-6">
    <h1 class="text-2xl font-semibold mb-6">Admin</h1>

    <section class="border border-gray-300 rounded p-4 mb-6">
      <h2 class="text-lg font-semibold mb-2">Initialize Database</h2>
      <p class="text-gray-700 mb-4">
        Drops and recreates the database schema from scratch. Destructive.
      </p>
      <button
        class="px-4 py-2 rounded bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
        :disabled="initStatus === 'loading'"
        @click="handleInit"
      >
        {{ initStatus === 'loading' ? 'Initializing...' : 'Initialize Database' }}
      </button>

      <p v-if="initStatus === 'done'" class="mt-3 text-green-700">
        Schema initialized: {{ JSON.stringify(initResult) }}
      </p>
      <p v-if="initStatus === 'error'" class="mt-3 text-red-700">{{ initError }}</p>
    </section>

    <section class="border border-gray-300 rounded p-4">
      <h2 class="text-lg font-semibold mb-2">Update Database</h2>
      <p class="text-gray-700 mb-4">
        Ingests any new dump heaps and runs the migration/projection pipeline.
      </p>
      <button
        class="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
        :disabled="isUpdateRunning"
        @click="handleUpdate"
      >
        {{ isUpdateRunning ? 'Update in progress...' : 'Update Database' }}
      </button>

      <div v-if="job" class="mt-4">
        <p>
          Status:
          <span
            class="font-semibold"
            :class="{
              'text-yellow-700': job.status === 'pending' || job.status === 'running',
              'text-green-700': job.status === 'succeeded',
              'text-red-700': job.status === 'failed',
            }"
          >{{ job.status }}</span>
        </p>
        <p v-if="job.status === 'succeeded'" class="text-gray-700 mt-1">
          {{ JSON.stringify(job.result) }}
        </p>
        <p v-if="job.status === 'failed'" class="text-red-700 mt-1">{{ job.error }}</p>

        <div v-if="job.logs.length" class="mt-3">
          <p class="text-sm font-semibold text-gray-700 mb-1">Logs</p>
          <pre
            ref="logContainer"
            class="bg-gray-50 border border-gray-200 text-gray-800 text-xs font-mono p-3 rounded max-h-64 overflow-y-auto whitespace-pre-wrap"
          >{{ job.logs.join('\n') }}</pre>
        </div>
      </div>

      <p v-if="updateError" class="mt-3 text-red-700">{{ updateError }}</p>
    </section>

    <section class="border border-gray-300 rounded p-4 mt-6">
      <h2 class="text-lg font-semibold mb-2">League Baselines</h2>
      <p class="text-gray-700 mb-4">
        This save's own recalibrated run-value constants (ticket 0066), recomputed from
        real MLB stats each time a yearly heap is ingested.
      </p>

      <p v-if="baselinesError" class="text-red-700">{{ baselinesError }}</p>
      <p v-else-if="baselines.length === 0" class="text-gray-500">
        No baselines computed yet — ingest at least one yearly heap.
      </p>
      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm text-left">
          <thead>
            <tr class="border-b border-gray-300 text-gray-600">
              <th class="py-1 pr-4">Computed</th>
              <th class="py-1 pr-4">Window</th>
              <th class="py-1 pr-4">lg_woba</th>
              <th class="py-1 pr-4">lg_pwoba</th>
              <th class="py-1 pr-4">ra9_baseline</th>
              <th class="py-1 pr-4">Batting PA</th>
              <th class="py-1 pr-4">Pitching BF</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in baselines"
              :key="row.id"
              class="border-b border-gray-100"
              :class="{ 'font-semibold': row.id === baselines[0].id }"
            >
              <td class="py-1 pr-4">{{ row.computed_at }}</td>
              <td class="py-1 pr-4">{{ row.window_start_year }}–{{ row.window_end_year }}</td>
              <td class="py-1 pr-4">{{ formatNumber(row.lg_woba, 4) }}</td>
              <td class="py-1 pr-4">{{ formatNumber(row.lg_pwoba, 4) }}</td>
              <td class="py-1 pr-4">{{ formatNumber(row.ra9_baseline, 3) }}</td>
              <td class="py-1 pr-4">{{ row.batting_pa_sample ?? '—' }}</td>
              <td class="py-1 pr-4">{{ row.pitching_bf_sample ?? '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="border border-gray-300 rounded p-4 mt-6">
      <h2 class="text-lg font-semibold mb-2">Market Baselines</h2>
      <p class="text-gray-700 mb-4">
        This save's own recalibrated contract-value constants (ticket 0066), recomputed from
        real contract data each time a yearly heap is ingested.
      </p>

      <p v-if="marketBaselinesError" class="text-red-700">{{ marketBaselinesError }}</p>
      <p v-else-if="marketBaselines.length === 0" class="text-gray-500">
        No baselines computed yet — ingest at least one yearly heap.
      </p>
      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm text-left">
          <thead>
            <tr class="border-b border-gray-300 text-gray-600">
              <th class="py-1 pr-4">Computed</th>
              <th class="py-1 pr-4">$/WAR</th>
              <th class="py-1 pr-4">$/WAR sample</th>
              <th class="py-1 pr-4">Extend threshold ($/yr)</th>
              <th class="py-1 pr-4">Threshold sample</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in marketBaselines"
              :key="row.id"
              class="border-b border-gray-100"
              :class="{ 'font-semibold': row.id === marketBaselines[0].id }"
            >
              <td class="py-1 pr-4">{{ row.computed_at }}</td>
              <td class="py-1 pr-4">{{ formatDollars(row.war_dollar_value) }}</td>
              <td class="py-1 pr-4">{{ row.war_dollar_value_sample ?? '—' }}</td>
              <td class="py-1 pr-4">{{ formatDollars(row.recommendation_extend_threshold) }}</td>
              <td class="py-1 pr-4">{{ row.threshold_cohort_sample ?? '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
