<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import ChoiceInputView from './ChoiceInputView.vue'
import type { Blocker, ChoiceStoryFragment, CostPreview, StoryFragment } from '@/types'
import { isRecord } from './fragmentUtils'

const props = defineProps<{
  choice: ChoiceStoryFragment
  fragments?: Record<string, StoryFragment>
  metadata?: Record<string, unknown>
  disabled?: boolean
}>()

const emit = defineEmits<{
  doAction: [edgeId: string, payload?: unknown]
}>()

const payloadValue = ref<unknown>(props.choice.payload)
const payloadValid = ref(true)

const choiceId = computed(() => props.choice.edge_id ?? props.choice.uid)
const available = computed(() => props.choice.available !== false && props.choice.active !== false)
const busy = computed(() => props.disabled === true)
const hotkey = computed(() => {
  const value = props.choice.ui_hints?.hotkey
  return typeof value === 'string' ? value : undefined
})
const iconName = computed(() => {
  const icon = props.choice.ui_hints?.icon ?? props.choice.icon
  if (typeof icon !== 'string' || !icon) {
    return undefined
  }
  return icon.startsWith('mdi-') ? icon : `mdi-${icon}`
})
const readableValue = (value: string): string => value.replace(/_/g, ' ')
const choiceHintBadges = computed(() => {
  const hints = props.choice.ui_hints ?? {}
  const badges: Array<{ key: string; label: string }> = []
  for (const key of ['source_kind', 'contribution', 'direction']) {
    const value = hints[key]
    if (typeof value === 'string' && value) {
      badges.push({ key, label: readableValue(value) })
    }
  }
  return badges
})
const timeDeltaLabel = computed(() => {
  const delta = props.choice.ui_hints?.time_delta
  if (!isRecord(delta)) {
    return undefined
  }
  const parts: string[] = []
  const periods = delta.periods
  if (typeof periods === 'number' && Number.isFinite(periods) && periods !== 0) {
    parts.push(`${periods > 0 ? '+' : ''}${periods} periods`)
  }
  const arrivesAt = delta.arrives_at
  if (typeof arrivesAt === 'string' && arrivesAt) {
    parts.push(`arrives ${readableValue(arrivesAt)}`)
  }
  return parts.length ? parts.join(' · ') : undefined
})
const isCostPreview = (value: unknown): value is CostPreview =>
  isRecord(value) &&
  typeof value.ledger_key === 'string' &&
  typeof value.delta === 'number' &&
  Number.isFinite(value.delta)
const costPreviewLabel = (preview: CostPreview): string => {
  const sign = preview.delta > 0 ? '+' : ''
  const unit = typeof preview.unit === 'string' && preview.unit ? ` ${preview.unit}` : ''
  return `${readableValue(preview.ledger_key)} ${sign}${preview.delta}${unit}`
}
const costPreviews = computed(() => {
  const previews: CostPreview[] = []
  const hintPreviews = props.choice.ui_hints?.cost_previews
  if (Array.isArray(hintPreviews)) {
    previews.push(...hintPreviews.filter(isCostPreview))
  }
  const accepts = props.choice.accepts
  if (isRecord(accepts) && Array.isArray(accepts.cost_previews)) {
    previews.push(...accepts.cost_previews.filter(isCostPreview))
  }
  return previews
})
const hasPayloadInput = computed(() => {
  const accepts = props.choice.accepts
  if (!accepts) {
    return false
  }
  const kind = 'kind' in accepts ? accepts.kind : undefined
  if (
    typeof kind === 'string' &&
    ['text', 'quantity', 'pieces', 'place', 'compose', 'raw_command'].includes(kind)
  ) {
    return true
  }
  return isRecord(accepts) && typeof accepts.input === 'string'
})
const canCommit = computed(() => available.value && !busy.value && payloadValid.value)

const blockers = computed<Blocker[]>(() => {
  const values = props.choice.blockers
  if (!Array.isArray(values)) {
    return []
  }
  return values.filter(
    (blocker): blocker is Blocker => isRecord(blocker) && typeof blocker.message === 'string',
  )
})

const buttonStyle = computed<Record<string, string | number> | undefined>(() => {
  const styleSource = props.choice.style ?? props.choice.style_dict
  if (!isRecord(styleSource)) {
    return undefined
  }

  const entries = Object.entries(styleSource).filter(([, value]) => {
    return typeof value === 'string' || typeof value === 'number'
  }) as Array<[string, string | number]>

  return entries.length ? Object.fromEntries(entries) : undefined
})

const handlePayloadChange = (payload: unknown, valid: boolean) => {
  payloadValue.value = payload
  payloadValid.value = valid
}

watch(
  () => props.choice,
  () => {
    payloadValue.value = props.choice.payload
    payloadValid.value = true
  },
  { deep: true },
)

const handleClick = () => {
  if (!canCommit.value) {
    return
  }
  emit('doAction', choiceId.value, payloadValue.value)
}
</script>

<template>
  <v-col cols="12" class="py-1">
    <div class="choice-row" :class="{ 'choice-row--locked': !available }">
      <v-btn
        class="ma-1 text-start choice-button"
        variant="outlined"
        color="primary"
        size="large"
        :style="buttonStyle"
        :disabled="!canCommit"
        :aria-disabled="!canCommit"
        :data-hotkey="hotkey"
        @click="handleClick"
      >
        <span v-if="hotkey" class="choice-hotkey">{{ hotkey }}</span>
        <v-icon v-if="iconName" :icon="iconName" start />
        <span>{{ choice.text }}</span>
      </v-btn>

      <ChoiceInputView
        v-if="hasPayloadInput"
        :choice="choice"
        :fragments="fragments ?? {}"
        :metadata="metadata"
        :disabled="!available || busy"
        @payload-change="handlePayloadChange"
        @commit="handleClick"
      />

      <div v-if="!available && choice.unavailable_reason" class="choice-reason">
        {{ choice.unavailable_reason }}
      </div>

      <div v-if="blockers.length" class="choice-blockers" data-testid="choice-blockers">
        <div
          v-for="blocker in blockers"
          :key="blocker.code ?? blocker.message"
          class="choice-blocker"
        >
          <span class="choice-blocker-message">{{ blocker.message }}</span>
          <span
            v-for="blockerRef in blocker.refs ?? []"
            :key="blockerRef"
            class="choice-blocker-ref"
          >
            {{ blockerRef }}
          </span>
        </div>
      </div>

      <div
        v-if="choiceHintBadges.length || timeDeltaLabel || costPreviews.length"
        class="choice-hints"
        data-testid="choice-hints"
      >
        <span
          v-for="badge in choiceHintBadges"
          :key="badge.key"
          class="choice-hint"
          data-testid="choice-hint"
        >
          {{ badge.label }}
        </span>
        <span
          v-if="timeDeltaLabel"
          class="choice-hint choice-hint--time"
          data-testid="choice-time-delta"
        >
          {{ timeDeltaLabel }}
        </span>
        <span
          v-for="preview in costPreviews"
          :key="`${preview.ledger_key}:${preview.delta}:${preview.unit ?? ''}`"
          class="choice-hint choice-hint--cost"
          :class="{ 'choice-hint--cost-up': preview.delta > 0, 'choice-hint--cost-down': preview.delta < 0 }"
          data-testid="choice-cost-preview"
        >
          {{ costPreviewLabel(preview) }}
        </span>
      </div>
    </div>
  </v-col>
</template>

<style scoped>
.choice-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 6px;
}

.choice-row--locked {
  opacity: 0.64;
}

.choice-button {
  min-height: 44px;
  white-space: normal;
  width: 100%;
}

.choice-hotkey {
  border: 1px solid currentColor;
  border-radius: 4px;
  font-size: 0.72rem;
  line-height: 1;
  margin-right: 8px;
  min-width: 22px;
  padding: 3px 5px;
  text-align: center;
}

.choice-reason {
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 0.78rem;
  padding: 0 8px 4px;
}

.choice-blockers {
  display: grid;
  gap: 4px;
  padding: 0 8px 2px;
}

.choice-blocker {
  align-items: center;
  color: rgb(var(--v-theme-error));
  display: flex;
  flex-wrap: wrap;
  font-size: 0.76rem;
  gap: 4px;
}

.choice-blocker-message {
  overflow-wrap: anywhere;
}

.choice-blocker-ref {
  border: 1px solid rgba(var(--v-theme-error), 0.28);
  border-radius: 4px;
  color: rgb(var(--v-theme-on-surface-variant));
  font-family: monospace;
  font-size: 0.68rem;
  padding: 1px 4px;
}

.choice-hints {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 0 8px 2px;
}

.choice-hint {
  border: 1px solid rgba(var(--v-theme-on-surface), 0.18);
  border-radius: 4px;
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 0.72rem;
  line-height: 1.1;
  padding: 3px 5px;
}

.choice-hint--time {
  color: rgb(var(--v-theme-primary));
}

.choice-hint--cost {
  font-family: monospace;
}

.choice-hint--cost-down {
  color: rgb(var(--v-theme-error));
}

.choice-hint--cost-up {
  color: rgb(var(--v-theme-success));
}
</style>
