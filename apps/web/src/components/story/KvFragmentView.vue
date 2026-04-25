<script setup lang="ts">
import type { StoryFragment } from '@/types'
import { fragmentText } from './fragmentUtils'
import { kvItems } from './fragmentViewUtils'

defineProps<{
  fragment: StoryFragment
}>()
</script>

<template>
  <div class="kv-strip" aria-label="scene status">
    <span v-for="item in kvItems(fragment)" :key="item[0]" class="kv-pair">
      <span>{{ item[0] }}</span>
      <b>{{ fragmentText(item[1]) }}</b>
    </span>
  </div>
</template>

<style scoped>
.kv-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 8px 16px;
}

.kv-pair {
  background: rgba(var(--v-theme-surface-variant), 0.6);
  border-radius: 5px;
  display: inline-flex;
  gap: 6px;
  padding: 4px 8px;
}
</style>
