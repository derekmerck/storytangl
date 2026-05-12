<script setup lang="ts">
import { computed } from 'vue'

import type { PieceStoryFragment } from '@/types'
import { fragmentText } from './fragmentUtils'

const props = defineProps<{
  fragment: PieceStoryFragment
}>()

const stringValue = (value: unknown): string | undefined =>
  typeof value === 'string' && value ? value : undefined

const readableValue = (value: string): string => value.replace(/_/g, ' ')

const hintLabel = computed(() => {
  const hints = props.fragment.hints ?? props.fragment.presentation_hints
  return stringValue(hints?.label_text)
})

const pieceLabel = computed(() => {
  const content = fragmentText(props.fragment.content)
  return (
    hintLabel.value ??
    stringValue(props.fragment.label) ??
    (content ? content : undefined) ??
    stringValue(props.fragment.piece_id) ??
    props.fragment.uid
  )
})

const displayState = computed(() => {
  const state = stringValue(props.fragment.display_state)
  return state ? readableValue(state) : undefined
})

const lifecycleState = computed(() => {
  if (props.fragment.realized === false) {
    return 'offer'
  }
  return undefined
})

const availabilityState = computed(() => {
  if (props.fragment.available === false) {
    return stringValue(props.fragment.unavailable_reason) ?? 'unavailable'
  }
  return undefined
})

const pieceKind = computed(() => {
  const kind = stringValue(props.fragment.kind)
  return kind ? readableValue(kind) : undefined
})
</script>

<template>
  <div
    class="piece-fragment"
    data-testid="piece-fragment"
    :data-piece-id="fragment.piece_id ?? fragment.uid"
  >
    <span class="piece-label">{{ pieceLabel }}</span>
    <span v-if="pieceKind" class="piece-meta">{{ pieceKind }}</span>
    <span v-if="displayState" class="piece-state" data-testid="piece-state">
      {{ displayState }}
    </span>
    <span
      v-if="lifecycleState"
      class="piece-state piece-state--offer"
      data-testid="piece-realized-state"
    >
      {{ lifecycleState }}
    </span>
    <span
      v-if="availabilityState"
      class="piece-state piece-state--locked"
      data-testid="piece-availability"
    >
      {{ availabilityState }}
    </span>
  </div>
</template>

<style scoped>
.piece-fragment {
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

.piece-label {
  font-weight: 700;
  overflow-wrap: anywhere;
}

.piece-meta,
.piece-state {
  border-radius: 4px;
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 0.75rem;
  line-height: 1.2;
  padding: 2px 5px;
}

.piece-meta {
  background: rgba(var(--v-theme-surface-variant), 0.62);
}

.piece-state {
  background: rgba(var(--v-theme-primary), 0.12);
}

.piece-state--offer {
  background: rgba(var(--v-theme-secondary), 0.14);
}

.piece-state--locked {
  background: rgba(var(--v-theme-error), 0.12);
  color: rgb(var(--v-theme-error));
}
</style>
