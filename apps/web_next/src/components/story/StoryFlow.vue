<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'

import StoryBlock from './StoryBlock.vue'
import type { DialogBlock, JournalAction, JournalStoryUpdate } from '@/types'
import { useGlobal } from '@/composables/globals'

const { $http, $debug, $verbose, remapURL, makeMediaDict } = useGlobal()

const blocks = ref<JournalStoryUpdate[]>([])
const blockRefs = ref<InstanceType<typeof StoryBlock>[]>([])
const blockCounter = ref(0)

const debugEnabled = computed(() => $debug.value && $verbose.value)

const remapMediaArray = (media?: JournalStoryUpdate['media']) => {
  if (!Array.isArray(media)) {
    return media
  }

  return media.map((item) => ({
    ...item,
    url: item.url ? remapURL(item.url) : item.url,
  }))
}

const cloneActions = (actions?: JournalAction[]) =>
  actions?.map((action) => ({ ...action })) ?? []

const processDialog = (dialog?: DialogBlock[]): DialogBlock[] => {
  if (!Array.isArray(dialog)) {
    return []
  }

  return dialog.map((item) => {
    const processed: DialogBlock = {
      ...item,
      media: remapMediaArray(item.media),
    }

    if (processed.media) {
      processed.media_dict = makeMediaDict(processed)
    }

    return processed
  })
}

const processBlock = (incoming: JournalStoryUpdate): JournalStoryUpdate => {
  blockCounter.value += 1

  const processed: JournalStoryUpdate = {
    ...incoming,
    key: `${incoming.uid}-${blockCounter.value}`,
    media: remapMediaArray(incoming.media),
    actions: cloneActions(incoming.actions),
  }

  if (processed.media) {
    processed.media_dict = makeMediaDict(processed)
  }

  if (incoming.dialog) {
    processed.dialog = processDialog(incoming.dialog)
  }

  return processed
}

const handleResponse = async (payload: JournalStoryUpdate[]) => {
  if (!Array.isArray(payload) || payload.length === 0) {
    return
  }

  if (payload[0]?.label) {
    blocks.value = []
  }

  const processedBlocks = payload.map((block) => processBlock(block))
  const startingIndex = blocks.value.length

  blocks.value.push(...processedBlocks)

  await nextTick(() => {
    const target = blockRefs.value[startingIndex]
    const element = target?.$el as HTMLElement | undefined

    element?.scrollIntoView({ behavior: startingIndex ? 'smooth' : 'auto' })
  })
}

const fetchInitialBlocks = async () => {
  try {
    const response = await $http.value.get<JournalStoryUpdate[]>('/story/update')
    await handleResponse(response.data)
  } catch (error) {
    console.error('Failed to fetch initial story.', error)
  }
}

onMounted(fetchInitialBlocks)

const doAction = async (
  _block: JournalStoryUpdate,
  actionUid: string,
  passback?: unknown,
) => {
  try {
    const response = await $http.value.post<JournalStoryUpdate[]>('/story/do', {
      uid: actionUid,
      passback,
    })
    await handleResponse(response.data)
  } catch (error) {
    console.error('Failed to execute action.', error)
  }
}
</script>

<template>
  <div>
    <StoryBlock
      v-for="block in blocks"
      :key="block.key"
      ref="blockRefs"
      :block="block"
      @doAction="doAction"
    />

    <v-card v-if="debugEnabled" class="mt-4">
      <v-card-item>
        <v-card border>
          <v-card-text class="text-caption">Blocks: {{ blocks }}</v-card-text>
        </v-card>
      </v-card-item>
    </v-card>
  </div>
</template>
