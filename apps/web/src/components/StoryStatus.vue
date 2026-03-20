<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { useGlobal } from '@/composables/globals'
import type {
  BadgeListValue,
  ItemListValue,
  KvListValue,
  PrimitiveValue,
  ProjectedSection,
  StoryStatus as StoryStatusPayload,
  TableValue,
} from '@/types'

type StatusItem = {
  key: string
  value?: string
}
type StatusSection = {
  sectionId: string
  title: string
  items: StatusItem[]
}

const { $http } = useGlobal()

const statusSections = ref<StatusSection[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

const formatPrimitive = (value: PrimitiveValue): string => {
  if (typeof value === 'boolean') {
    return value ? 'yes' : 'no'
  }
  return String(value)
}

const normalizeKvList = (value: KvListValue): StatusItem[] =>
  value.items.map((item) => ({
    key: item.key,
    value: formatPrimitive(item.value),
  }))

const normalizeItemList = (value: ItemListValue): StatusItem[] =>
  value.items.map((item) => {
    const extras = [item.detail, item.tags?.length ? item.tags.join(', ') : undefined].filter(Boolean)
    return {
      key: item.label,
      value: extras.length ? extras.join(' | ') : undefined,
    }
  })

const normalizeTable = (value: TableValue): StatusItem[] =>
  value.rows.map((row, index) => ({
    key: `Row ${index + 1}`,
    value: row
      .map((cell, cellIndex) => `${value.columns[cellIndex]}: ${formatPrimitive(cell)}`)
      .join(' | '),
  }))

const normalizeBadges = (value: BadgeListValue): StatusItem[] =>
  value.items.length ? [{ key: 'Values', value: value.items.join(', ') }] : []

const normalizeSection = (section: ProjectedSection): StatusSection => {
  const value = section.value

  if (value.value_type === 'kv_list') {
    return { sectionId: section.section_id, title: section.title, items: normalizeKvList(value) }
  }
  if (value.value_type === 'item_list') {
    return { sectionId: section.section_id, title: section.title, items: normalizeItemList(value) }
  }
  if (value.value_type === 'table') {
    return { sectionId: section.section_id, title: section.title, items: normalizeTable(value) }
  }
  if (value.value_type === 'badges') {
    return { sectionId: section.section_id, title: section.title, items: normalizeBadges(value) }
  }

  return {
    sectionId: section.section_id,
    title: section.title,
    items: [{ key: 'Value', value: formatPrimitive(value.value) }],
  }
}

const normalizeStatusPayload = (payload: StoryStatusPayload | null | undefined): StatusSection[] => {
  if (!payload?.sections?.length) {
    return []
  }
  return payload.sections.map(normalizeSection)
}

onMounted(async () => {
  try {
    loading.value = true
    error.value = null
    const response = await $http.value.get<StoryStatusPayload>('/story/info')
    statusSections.value = normalizeStatusPayload(response.data)
  } catch (err) {
    console.error('Failed to fetch status:', err)
    error.value = 'Unable to load story status. Please try again later.'
    statusSections.value = []
  } finally {
    loading.value = false
  }
})

const hasSections = computed(() => statusSections.value.length > 0)
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

    <div v-else-if="hasSections">
      <div v-for="section in statusSections" :key="section.sectionId" class="mb-2">
        <div class="text-overline text-medium-emphasis px-4 pt-2">
          {{ section.title }}
        </div>

        <v-list density="compact">
          <v-list-item v-for="item in section.items" :key="`${section.sectionId}-${item.key}`">
            <v-list-item-title class="text-body-2 font-weight-medium">
              {{ item.key }}
            </v-list-item-title>

            <v-list-item-subtitle v-if="item.value">
              {{ item.value }}
            </v-list-item-subtitle>
          </v-list-item>
        </v-list>
      </div>
    </div>

    <div v-else class="text-caption text-medium-emphasis px-4 py-2">
      No status data available.
    </div>
  </div>
</template>
