<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { AdminApiError, getJob, initDatabase, updateDatabase } from '@/api/admin'
import type { Job } from '@/api/admin'

const POLL_INTERVAL_MS = 2000

const initStatus = ref<'idle' | 'loading' | 'done' | 'error'>('idle')
const initResult = ref<unknown>(null)
const initError = ref<string | null>(null)

const job = ref<Job | null>(null)
const updateError = ref<string | null>(null)
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
  }
  pollHandle = setInterval(() => pollJob(jobId), POLL_INTERVAL_MS)
  pollJob(jobId)
}

async function pollJob(jobId: string) {
  try {
    job.value = await getJob(jobId)
    if (job.value.status === 'succeeded' || job.value.status === 'failed') {
      stopPolling()
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
      </div>

      <p v-if="updateError" class="mt-3 text-red-700">{{ updateError }}</p>
    </section>
  </div>
</template>
