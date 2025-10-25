<script setup lang="ts">
import { computed } from 'vue'

import type { DialogBlock } from '@/types'

/**
 * StoryDialogBlock - renders an individual dialog entry with optional speaker metadata.
 */
const props = defineProps<{
  dialog_block: DialogBlock
}>()

const avatarUrl = computed(() => props.dialog_block.media_dict?.avatar_im?.url)
const hasAvatar = computed(() => Boolean(avatarUrl.value))

const textStyle = computed<Record<string, string | number> | undefined>(() => {
  const styleSource = props.dialog_block.style ?? props.dialog_block.style_dict
  if (!styleSource) {
    return undefined
  }

  const entries = Object.entries(styleSource).filter(([, value]) => {
    return typeof value === 'string' || typeof value === 'number'
  }) as Array<[string, string | number]>

  return entries.length ? Object.fromEntries(entries) : undefined
})
</script>

<template>
  <v-col cols="12" class="py-1">
    <v-row align="center" class="gap-3 flex-nowrap">
      <v-col v-if="hasAvatar" cols="auto" class="flex-grow-0">
        <v-avatar size="56">
          <img :src="avatarUrl" alt="" class="w-100 h-100 object-cover" />
        </v-avatar>
      </v-col>

      <v-col class="py-0">
        <div v-if="dialog_block.label" class="text-body-2 font-weight-medium mb-1">
          {{ dialog_block.label }}
        </div>
        <div class="text-body-2" :style="textStyle" v-html="dialog_block.text" />
      </v-col>
    </v-row>
  </v-col>
</template>
