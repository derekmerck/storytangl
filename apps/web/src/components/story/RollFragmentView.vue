<script setup lang="ts">
import { computed } from 'vue'

import type { RollStoryFragment } from '@/types'
import { fragmentText, isRecord } from './fragmentUtils'

const props = defineProps<{
  fragment: RollStoryFragment
}>()

const stringValue = (value: unknown): string | undefined =>
  typeof value === 'string' && value ? value : undefined

const numberValue = (value: unknown): number | undefined =>
  typeof value === 'number' && Number.isFinite(value) ? value : undefined

const readableValue = (value: string): string => value.replace(/_/g, ' ')

const inputs = computed(() =>
  isRecord(props.fragment.inputs) ? props.fragment.inputs : {},
)

const label = computed(() =>
  stringValue(props.fragment.label) ??
  stringValue(props.fragment.content) ??
  'Roll',
)

const rollKind = computed(() => stringValue(props.fragment.kind) ?? 'roll')

const outcome = computed(() => {
  const value = stringValue(props.fragment.outcome)
  return value ? readableValue(value) : 'unknown'
})

const diceSummary = computed(() => {
  const dice = stringValue(inputs.value.dice)
  const rolled = Array.isArray(inputs.value.rolled) ? inputs.value.rolled : []
  const total = numberValue(inputs.value.total)
  const target = numberValue(inputs.value.target)
  const modifier = numberValue(inputs.value.modifier)
  if (!dice || rolled.length === 0 || total === undefined) {
    return undefined
  }
  const rolledText = rolled.map((value) => String(value)).join(' + ')
  const modifierText = modifier ? ` ${modifier > 0 ? '+' : ''}${modifier}` : ''
  const targetText = target === undefined ? '' : ` vs ${target}`
  return `${dice}: ${rolledText}${modifierText} = ${total}${targetText}`
})

const fallbackInputSummary = computed(() => {
  if (diceSummary.value) {
    return undefined
  }
  return Object.keys(inputs.value).length > 0 ? fragmentText(inputs.value) : undefined
})

const narrative = computed(() => stringValue(props.fragment.narrative))
</script>

<template>
  <section class="roll-fragment" data-testid="roll-fragment" :data-outcome="outcome">
    <header class="roll-header">
      <span class="roll-kind">{{ rollKind }}</span>
      <span class="roll-label">{{ label }}</span>
      <span class="roll-outcome">{{ outcome }}</span>
    </header>
    <div v-if="diceSummary || fallbackInputSummary" class="roll-summary">
      {{ diceSummary ?? fallbackInputSummary }}
    </div>
    <div v-if="narrative" class="roll-narrative">{{ narrative }}</div>
  </section>
</template>

<style scoped>
.roll-fragment {
  background: rgba(var(--v-theme-surface-variant), 0.2);
  border: 1px solid rgba(var(--v-theme-primary), 0.26);
  border-radius: 6px;
  margin: 8px 16px;
  padding: 10px 12px;
}

.roll-header {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.roll-kind,
.roll-outcome {
  border-radius: 4px;
  font-size: 0.75rem;
  line-height: 1.2;
  padding: 2px 6px;
  text-transform: uppercase;
}

.roll-kind {
  background: rgba(var(--v-theme-surface), 0.9);
  color: rgb(var(--v-theme-on-surface-variant));
}

.roll-label {
  font-weight: 800;
  overflow-wrap: anywhere;
}

.roll-outcome {
  background: rgba(var(--v-theme-primary), 0.14);
  color: rgb(var(--v-theme-primary));
  font-weight: 700;
}

.roll-summary {
  color: rgb(var(--v-theme-on-surface-variant));
  font-family: monospace;
  font-size: 0.86rem;
  margin-top: 6px;
  overflow-wrap: anywhere;
}

.roll-narrative {
  margin-top: 6px;
}
</style>
