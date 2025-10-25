<script setup lang="ts">
import { computed } from 'vue'

import StoryAction from './StoryAction.vue'
import StoryDialogBlock from './StoryDialogBlock.vue'
import type { JournalStoryUpdate, JournalAction, DialogBlock } from '@/types'
import { useGlobal } from '@/composables/globals'

/**
 * StoryBlock - renders a narrative block including dialog, media, and actions.
 */
const props = defineProps<{
  block: JournalStoryUpdate
}>()

const emit = defineEmits<{
  doAction: [block: JournalStoryUpdate, uid: string, passback?: unknown]
}>()

const { $debug, $verbose } = useGlobal()

const actions = computed<JournalAction[]>(() => props.block.actions ?? [])
const hasActions = computed(() => actions.value.length > 0)
const hasDialog = computed(() => (props.block.dialog?.length ?? 0) > 0)

const narrativeMedia = computed(() => {
  if (props.block.media_dict?.narrative_im) {
    return props.block.media_dict.narrative_im
  }

  return props.block.media?.find((item) => item.media_role === 'narrative_im') ?? null
})

const hasLandscapeImage = computed(() => narrativeMedia.value?.orientation === 'landscape')
const hasInlineImage = computed(() => Boolean(narrativeMedia.value) && !hasLandscapeImage.value)
const imageColumnSize = computed(() => (narrativeMedia.value?.orientation === 'portrait' ? 4 : 5))

const shouldShowText = computed(() => Boolean(props.block.text) && !hasDialog.value)

const dialogBlocks = computed<DialogBlock[]>(() => props.block.dialog ?? [])

const debugEnabled = computed(() => $debug.value && $verbose.value)

const handleAction = (uid: string, passback?: unknown) => {
  emit('doAction', props.block, uid, passback)
}
</script>

<template>
  <v-card class="mb-4">
    <v-card-item v-if="hasLandscapeImage" class="mx-5 mt-5">
      <v-parallax :src="narrativeMedia?.url" cover height="50vh" scale="0.5" />
    </v-card-item>

    <v-card-title v-if="block.title" class="subtitle mx-5 mt-5">
      {{ block.title }}
    </v-card-title>

    <v-card-item>
      <v-row align="stretch" justify="center">
        <v-col>
          <v-card-text v-if="shouldShowText" v-html="block.text" />

          <v-row v-if="hasDialog" class="g-0">
            <StoryDialogBlock v-for="dialog in dialogBlocks" :key="dialog.uid" :dialog_block="dialog" />
          </v-row>

          <v-card-actions v-if="hasActions">
            <v-row dense>
              <StoryAction v-for="action in actions" :key="action.uid" :action="action" @doAction="handleAction" />
            </v-row>
          </v-card-actions>
        </v-col>

        <v-col
          v-if="hasInlineImage"
          cols="12"
          :md="imageColumnSize"
          class="mr-5"
          order="first"
          order-md="last"
        >
          <v-img :src="narrativeMedia?.url" :style="{ maxHeight: '70vh' }" cover />
        </v-col>
      </v-row>
    </v-card-item>

    <v-card-item v-if="debugEnabled">
      <v-card border>
        <v-card-text class="text-caption">
          Block: {{ block }}
        </v-card-text>
      </v-card>
    </v-card-item>
  </v-card>
</template>
