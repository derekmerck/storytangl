<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { useGlobal } from '@/composables/globals'
import type { JournalKVItem, StoryStatus as StoryStatusPayload } from '@/types'

type StatusItem = JournalKVItem & { style?: Record<string, string | number> }

const { $http } = useGlobal()

const statusItems = ref<StatusItem[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

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

onMounted(async () => {
  try {
    loading.value = true
    error.value = null
    const response = await $http.value.get<StoryStatusPayload>('/story/status')
    statusItems.value = (response.data ?? []).map((item) => ({
      ...item,
      style: normaliseStyle(item),
    }))
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
