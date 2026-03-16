<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { useGlobal } from '@/composables/globals'
import type { JournalKVItem, RuntimeInfo, StoryStatus as StoryStatusPayload } from '@/types'

type StatusItem = JournalKVItem & { style?: Record<string, string | number> }
type StatusValue = number | string | unknown[]

const { $http } = useGlobal()

const statusItems = ref<StatusItem[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

const STATUS_KEY_LABELS: Record<string, string> = {
  status: 'status',
  message: 'message',
  cursor_label: 'location',
  turn: 'turn',
  step: 'step',
  choice_steps: 'choices made',
  cursor_steps: 'moves',
  journal_size: 'journal entries',
  last_redirect: 'last redirect',
  redirect_trace: 'redirect trace',
}

const STATUS_KEY_ICONS: Record<string, string> = {
  status: 'check-circle',
  cursor_label: 'map-marker',
  turn: 'timeline-outline',
  step: 'counter',
  choice_steps: 'source-branch',
  journal_size: 'book-open-page-variant',
}

const normaliseStyle = (item: JournalKVItem) => {
  const source = item.style ?? item.style_dict
  if (!source) {
    return undefined
  }

  const entries = Object.entries(source).filter(([, value]) => {
    return typeof value === 'string' || typeof value === 'number'
  }) as Array<[string, string | number]>

  return entries.length ? Object.fromEntries(entries) : undefined
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

const formatValue = (value: unknown): StatusValue | undefined => {
  if (value === null || value === undefined || value === '') {
    return undefined
  }
  if (Array.isArray(value)) {
    return value.length ? value : undefined
  }
  if (typeof value === 'number' || typeof value === 'string') {
    return value
  }
  if (typeof value === 'boolean') {
    return value ? 'yes' : 'no'
  }
  if (isRecord(value)) {
    const entries = Object.entries(value)
    return entries.length ? JSON.stringify(value) : undefined
  }
  return String(value)
}

const statusStyleFor = (key: string, value: StatusValue | undefined) => {
  if (key === 'status' && value === 'ok') {
    return { color: 'rgb(var(--v-theme-success))', fontWeight: 600 }
  }
  if (key === 'status' && value === 'error') {
    return { color: 'rgb(var(--v-theme-error))', fontWeight: 600 }
  }
  return undefined
}

const normalizeRuntimeStatus = (payload: RuntimeInfo): StatusItem[] => {
  const orderedKeys = [
    'status',
    'message',
    'cursor_label',
    'turn',
    'step',
    'choice_steps',
    'cursor_steps',
    'journal_size',
    'last_redirect',
    'redirect_trace',
  ]
  const ignoredKeys = new Set(['code', 'cursor_id', 'details'])
  const items: StatusItem[] = []
  const pushItem = (key: string, rawValue: unknown) => {
    const value = formatValue(rawValue)
    if (value === undefined) {
      return
    }
    items.push({
      key: STATUS_KEY_LABELS[key] ?? key,
      value,
      icon: STATUS_KEY_ICONS[key],
      style: statusStyleFor(key, value),
    })
  }

  for (const key of orderedKeys) {
    pushItem(key, payload[key])
  }

  const details = isRecord(payload.details) ? payload.details : null
  if (details) {
    for (const key of Object.keys(details)) {
      if (orderedKeys.includes(key) || ignoredKeys.has(key)) {
        continue
      }
      pushItem(key, details[key])
    }
  }

  for (const [key, value] of Object.entries(payload)) {
    if (orderedKeys.includes(key) || ignoredKeys.has(key)) {
      continue
    }
    pushItem(key, value)
  }

  return items
}

const normalizeStatusPayload = (payload: StoryStatusPayload | null | undefined): StatusItem[] => {
  if (Array.isArray(payload)) {
    return payload.map((item) => ({
      ...item,
      style: normaliseStyle(item),
    }))
  }

  if (isRecord(payload)) {
    return normalizeRuntimeStatus(payload as RuntimeInfo)
  }

  return []
}

onMounted(async () => {
  try {
    loading.value = true
    error.value = null
    const response = await $http.value.get<StoryStatusPayload>('/story/info')
    statusItems.value = normalizeStatusPayload(response.data)
  } catch (err) {
    console.error('Failed to fetch status:', err)
    error.value = 'Unable to load story status. Please try again later.'
    statusItems.value = []
  } finally {
    loading.value = false
  }
})

const hasItems = computed(() => statusItems.value.length > 0)
</script>

<template>
  <div>
    <v-progress-linear v-if="loading" color="primary" indeterminate />

    <v-alert
      v-else-if="error"
      type="error"
      variant="tonal"
      class="mb-2"
      closable
      @click:close="error = null"
    >
      {{ error }}
    </v-alert>

    <v-list v-else-if="hasItems" density="compact">
      <v-list-item v-for="item in statusItems" :key="item.key">
        <template #prepend>
          <v-icon v-if="item.icon" :icon="item.icon.startsWith('mdi-') ? item.icon : `mdi-${item.icon}`" />
        </template>

        <v-list-item-title class="text-body-2 font-weight-medium">
          {{ item.key }}
        </v-list-item-title>

        <v-list-item-subtitle :style="item.style">
          {{ item.value }}
        </v-list-item-subtitle>
      </v-list-item>
    </v-list>

    <div v-else class="text-caption text-medium-emphasis px-4 py-2">
      No status data available.
    </div>
  </div>
</template>
