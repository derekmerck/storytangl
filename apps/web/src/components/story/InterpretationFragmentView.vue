<script setup lang="ts">
import { computed } from 'vue'

import type { InterpretationStoryFragment } from '@/types'

const props = defineProps<{
  fragment: InterpretationStoryFragment
}>()

const stringValue = (value: unknown): string | undefined =>
  typeof value === 'string' && value ? value : undefined

const readableValue = (value: string): string => value.replace(/_/g, ' ')

const result = computed(() => {
  const value = stringValue(props.fragment.result)
  return value ? readableValue(value) : 'command feedback'
})

const commandText = computed(() => stringValue(props.fragment.text))
const message = computed(() => stringValue(props.fragment.message))
const blockedReason = computed(() => stringValue(props.fragment.blocked_reason))
const hint = computed(() => stringValue(props.fragment.hint))
const candidates = computed(() =>
  Array.isArray(props.fragment.candidates)
    ? props.fragment.candidates.filter((candidate): candidate is string => typeof candidate === 'string')
    : [],
)
</script>

<template>
  <section
    class="interpretation-fragment"
    data-testid="interpretation-fragment"
  >
    <header class="interpretation-header">
      <span class="interpretation-result">{{ result }}</span>
      <code
        v-if="commandText"
        class="interpretation-command"
      >
        {{ commandText }}
      </code>
    </header>

    <p
      v-if="message"
      class="interpretation-message"
    >
      {{ message }}
    </p>
    <p
      v-if="blockedReason"
      class="interpretation-detail"
    >
      {{ blockedReason }}
    </p>
    <p
      v-if="hint"
      class="interpretation-hint"
    >
      {{ hint }}
    </p>

    <div
      v-if="candidates.length"
      class="interpretation-candidates"
    >
      <span
        v-for="(candidate, index) in candidates"
        :key="`${candidate}-${index}`"
        class="interpretation-candidate"
      >
        {{ candidate }}
      </span>
    </div>
  </section>
</template>

<style scoped>
.interpretation-fragment {
  background: rgba(var(--v-theme-warning), 0.08);
  border: 1px solid rgba(var(--v-theme-warning), 0.32);
  border-radius: 6px;
  margin: 8px 16px;
  padding: 10px 12px;
}

.interpretation-header {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.interpretation-result {
  background: rgba(var(--v-theme-warning), 0.18);
  border-radius: 4px;
  color: rgb(var(--v-theme-on-surface));
  font-size: 0.75rem;
  font-weight: 700;
  line-height: 1.2;
  padding: 2px 6px;
  text-transform: uppercase;
}

.interpretation-command {
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 0.82rem;
  overflow-wrap: anywhere;
}

.interpretation-message,
.interpretation-detail,
.interpretation-hint {
  margin: 6px 0 0;
}

.interpretation-detail,
.interpretation-hint {
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 0.86rem;
}

.interpretation-candidates {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 8px;
}

.interpretation-candidate {
  border: 1px solid rgba(var(--v-theme-on-surface), 0.18);
  border-radius: 4px;
  color: rgb(var(--v-theme-on-surface-variant));
  font-family: monospace;
  font-size: 0.74rem;
  padding: 2px 5px;
}
</style>
