<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import { useGlobal } from '@/composables/globals'
import type {
  BadgeListValue,
  ItemListValue,
  KvListValue,
  InfoAffordance,
  PrimitiveValue,
  ProjectedSection,
  StoryStatus as StoryStatusPayload,
  TableValue,
} from '@/types'

type StatusItem = {
  key: string
  value?: string
  tags?: string[]
}
type StatusSection = {
  sectionId: string
  title: string
  kind?: string | null
  items: StatusItem[]
}

const { $http } = useGlobal()

const props = defineProps<{
  refreshKey?: string | number
  infoAffordances?: InfoAffordance[]
}>()

const statusSections = ref<StatusSection[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const activeAffordanceKind = ref<string | null>(null)

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
    return {
      key: item.label,
      value: item.detail ?? undefined,
      tags: item.tags,
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
  const base = { sectionId: section.section_id, title: section.title, kind: section.kind }

  if (value.value_type === 'kv_list') {
    return { ...base, items: normalizeKvList(value) }
  }
  if (value.value_type === 'item_list') {
    return { ...base, items: normalizeItemList(value) }
  }
  if (value.value_type === 'table') {
    return { ...base, items: normalizeTable(value) }
  }
  if (value.value_type === 'badges') {
    return { ...base, items: normalizeBadges(value) }
  }

  return {
    ...base,
    items: [{ key: 'Value', value: formatPrimitive(value.value) }],
  }
}

const normalizeStatusPayload = (payload: StoryStatusPayload | null | undefined): StatusSection[] => {
  if (!payload?.sections?.length) {
    return []
  }
  return payload.sections.map(normalizeSection)
}

type QueryParamValue = string | number | boolean | Array<string | number | boolean>
type QueryParams = Record<string, QueryParamValue>

const isQueryParamValue = (value: unknown): value is QueryParamValue => {
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return true
  }
  return (
    Array.isArray(value) &&
    value.every(
      (item) => typeof item === 'string' || typeof item === 'number' || typeof item === 'boolean',
    )
  )
}

const affordanceLabel = (affordance: InfoAffordance): string =>
  affordance.label ?? affordance.kind.replace(/_/g, ' ')

const activeAffordance = computed(() =>
  props.infoAffordances?.find((affordance) => affordance.kind === activeAffordanceKind.value),
)

const infoQueryParams = (affordance: InfoAffordance | undefined): QueryParams | undefined => {
  if (!affordance) {
    return undefined
  }
  const params: QueryParams = {}
  if (affordance.query) {
    for (const [key, value] of Object.entries(affordance.query)) {
      if (key && isQueryParamValue(value)) {
        params[key] = value
      }
    }
  }
  if (!('type' in params) && !('kind' in params) && !('kinds' in params)) {
    params.type = affordance.kind
  }
  if (affordance.format && !('format' in params)) {
    params.format = affordance.format
  }
  return params
}

const loadStatus = async (affordance: InfoAffordance | undefined = activeAffordance.value) => {
  try {
    loading.value = true
    error.value = null
    const response = await $http.value.get<StoryStatusPayload>('/story/info', {
      params: infoQueryParams(affordance),
    })
    statusSections.value = normalizeStatusPayload(response.data)
  } catch (err) {
    console.error('Failed to fetch status:', err)
    error.value = 'Unable to load story status. Please try again later.'
    statusSections.value = []
  } finally {
    loading.value = false
  }
}

const hasSections = computed(() => statusSections.value.length > 0)
const hasAffordances = computed(() => Boolean(props.infoAffordances?.length))

const sectionClass = (section: StatusSection): Record<string, boolean> => {
  const kind = section.kind ?? section.sectionId
  return {
    'story-status-section--world-time': kind === 'world_time',
    'story-status-section--location': kind === 'location',
    'story-status-section--agenda': kind === 'agenda' || kind === 'schedule',
  }
}

onMounted(loadStatus)

watch(
  () => props.refreshKey,
  () => {
    void loadStatus()
  },
)

watch(
  () => props.infoAffordances,
  (affordances) => {
    if (
      activeAffordanceKind.value &&
      !affordances?.some((affordance) => affordance.kind === activeAffordanceKind.value)
    ) {
      activeAffordanceKind.value = null
      void loadStatus(undefined)
    }
  },
)

const selectAffordance = (affordance: InfoAffordance | undefined) => {
  activeAffordanceKind.value = affordance?.kind ?? null
  void loadStatus(affordance)
}
</script>

<template>
  <div>
    <div
      v-if="hasAffordances"
      class="info-affordance-bar px-3 pb-2"
      data-testid="info-affordance-bar"
      aria-label="story info"
    >
      <v-btn
        class="info-affordance"
        size="x-small"
        variant="text"
        :color="activeAffordanceKind === null ? 'primary' : undefined"
        :aria-pressed="activeAffordanceKind === null"
        @click="selectAffordance(undefined)"
      >
        Status
      </v-btn>
      <v-btn
        v-for="affordance in infoAffordances"
        :key="affordance.kind"
        class="info-affordance"
        size="x-small"
        variant="text"
        :color="activeAffordanceKind === affordance.kind ? 'primary' : undefined"
        :aria-pressed="activeAffordanceKind === affordance.kind"
        :data-info-kind="affordance.kind"
        @click="selectAffordance(affordance)"
      >
        {{ affordanceLabel(affordance) }}
        <span v-if="affordance.shortcuts?.length" class="info-affordance-shortcut">
          {{ affordance.shortcuts[0] }}
        </span>
      </v-btn>
    </div>

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
      <div
        v-for="section in statusSections"
        :key="section.sectionId"
        class="story-status-section mb-2"
        :class="sectionClass(section)"
        :data-section-kind="section.kind ?? section.sectionId"
      >
        <div class="story-status-heading text-overline text-medium-emphasis px-4 pt-2">
          <span>{{ section.title }}</span>
          <span
            v-if="section.kind && section.kind !== section.sectionId"
            class="story-status-kind"
          >
            {{ section.kind }}
          </span>
        </div>

        <v-list density="compact">
          <v-list-item
            v-for="item in section.items"
            :key="`${section.sectionId}-${item.key}`"
            class="story-status-item"
          >
            <v-list-item-title class="text-body-2 font-weight-medium">
              {{ item.key }}
            </v-list-item-title>

            <v-list-item-subtitle v-if="item.value">
              {{ item.value }}
            </v-list-item-subtitle>

            <div v-if="item.tags?.length" class="story-status-tags">
              <span v-for="tag in item.tags" :key="tag" class="story-status-tag">
                {{ tag }}
              </span>
            </div>
          </v-list-item>
        </v-list>
      </div>
    </div>

    <div v-else class="text-caption text-medium-emphasis px-4 py-2">
      No status data available.
    </div>
  </div>
</template>

<style scoped>
.story-status-heading {
  align-items: center;
  display: flex;
  gap: 8px;
  justify-content: space-between;
}

.info-affordance-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.info-affordance {
  min-width: 0;
}

.info-affordance-shortcut {
  border: 1px solid currentColor;
  border-radius: 4px;
  font-size: 0.64rem;
  line-height: 1;
  margin-left: 5px;
  opacity: 0.72;
  padding: 1px 3px;
}

.story-status-kind {
  border: 1px solid rgba(var(--v-theme-on-surface), 0.18);
  border-radius: 4px;
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 0.64rem;
  line-height: 1;
  padding: 2px 4px;
  text-transform: none;
}

.story-status-section--world-time :deep(.v-list) {
  background: rgba(var(--v-theme-primary), 0.06);
}

.story-status-section--agenda :deep(.v-list),
.story-status-section--location :deep(.v-list) {
  background: rgba(var(--v-theme-surface-variant), 0.2);
}

.story-status-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}

.story-status-tag {
  border: 1px solid rgba(var(--v-theme-on-surface), 0.18);
  border-radius: 4px;
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 0.68rem;
  line-height: 1.1;
  padding: 2px 4px;
}
</style>
