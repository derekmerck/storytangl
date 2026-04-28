<script setup lang="ts">
import { computed } from 'vue'

import type { TokenStoryFragment } from '@/types'
import { fragmentText } from './fragmentUtils'

const props = defineProps<{
  fragment: TokenStoryFragment
}>()

const stringValue = (value: unknown): string | undefined =>
  typeof value === 'string' && value ? value : undefined

const readableValue = (value: string): string => value.replace(/_/g, ' ')

const hintLabel = computed(() => {
  const hints = props.fragment.hints ?? props.fragment.presentation_hints
  return stringValue(hints?.label_text)
})

const tokenLabel = computed(() => {
  const content = fragmentText(props.fragment.content)
  return (
    hintLabel.value ??
    stringValue(props.fragment.label) ??
    (content ? content : undefined) ??
    stringValue(props.fragment.token_id) ??
    props.fragment.uid
  )
})

const displayState = computed(() => {
  const state = stringValue(props.fragment.display_state)
  return state ? readableValue(state) : undefined
})

const tokenKind = computed(() => {
  const kind = stringValue(props.fragment.kind)
  return kind ? readableValue(kind) : undefined
})
</script>

<template>
  <div
    class="token-fragment"
    data-testid="token-fragment"
    :data-token-id="fragment.token_id ?? fragment.uid"
  >
    <span class="token-label">{{ tokenLabel }}</span>
    <span v-if="tokenKind" class="token-meta">{{ tokenKind }}</span>
    <span v-if="displayState" class="token-state" data-testid="token-state">
      {{ displayState }}
    </span>
  </div>
</template>

<style scoped>
.token-fragment {
  align-items: center;
  background: rgba(var(--v-theme-surface), 0.86);
  border: 1px solid rgba(var(--v-theme-primary), 0.34);
  border-radius: 6px;
  box-shadow: 0 1px 0 rgba(var(--v-theme-on-surface), 0.06);
  display: inline-flex;
  flex-wrap: wrap;
  gap: 6px;
  min-height: 34px;
  min-width: 0;
  padding: 6px 9px;
}

.token-label {
  font-weight: 700;
  overflow-wrap: anywhere;
}

.token-meta,
.token-state {
  border-radius: 4px;
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 0.75rem;
  line-height: 1.2;
  padding: 2px 5px;
}

.token-meta {
  background: rgba(var(--v-theme-surface-variant), 0.62);
}

.token-state {
  background: rgba(var(--v-theme-primary), 0.12);
}
</style>
