<script setup lang="ts">
import type { StoryFragment } from '@/types'
import { fragmentText } from './fragmentUtils'
import { contentClass } from './fragmentViewUtils'

defineProps<{
  fragment: StoryFragment
}>()
</script>

<template>
  <v-card-text :class="contentClass(fragment)">
    <div v-html="fragmentText(fragment.content)" />
  </v-card-text>
</template>
