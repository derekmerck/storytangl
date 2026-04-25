<script setup lang="ts">
import type { StoryFragment } from '@/types'
import { fragmentText } from './fragmentUtils'

defineProps<{
  fragment: StoryFragment
}>()
</script>

<template>
  <div class="fragment-fallback" data-testid="fragment-fallback">
    <span class="fragment-fallback-label">{{ fragment.fragment_type }}</span>
    {{ fragmentText(fragment.content) }}
  </div>
</template>

<style scoped>
.fragment-fallback {
  border: 1px dashed rgba(var(--v-theme-on-surface), 0.32);
  border-radius: 6px;
  color: rgb(var(--v-theme-on-surface-variant));
  font-family: monospace;
  font-size: 0.82rem;
  margin: 8px 16px;
  padding: 10px 12px;
}

.fragment-fallback-label {
  color: rgb(var(--v-theme-primary));
  font-weight: 700;
  margin-right: 6px;
}
</style>
