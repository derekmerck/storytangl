<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'

import StoryBlock from './StoryBlock.vue'
import type { DialogBlock, JournalAction, JournalStoryUpdate, MediaRole } from '@/types'
import { useGlobal } from '@/composables/globals'

const { $http, $debug, $verbose, remapURL, makeMediaDict } = useGlobal()
const storyRoutePrefix = import.meta.env.VITE_STORY_ROUTE_PREFIX || '/story'

type UnknownRecord = Record<string, unknown>
const MEDIA_ROLES: readonly MediaRole[] = [
  'none',
  'image',
  'narrative_im',
  'info_im',
  'logo_im',
  'portrait_im',
  'avatar_im',
  'dialog_im',
  'cover_im',
  'audio',
  'voice_over',
  'dialog_vo',
  'music',
  'sfx',
  'video',
  'animation',
]
const MEDIA_ROLE_SET: ReadonlySet<MediaRole> = new Set(MEDIA_ROLES)

const blocks = ref<JournalStoryUpdate[]>([])
const blockRefs = ref<InstanceType<typeof StoryBlock>[]>([])
const blockCounter = ref(0)
const loading = ref(false)
const error = ref<string | null>(null)

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

const isRecord = (value: unknown): value is UnknownRecord =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

const isMediaRole = (value: unknown): value is MediaRole =>
  typeof value === 'string' && MEDIA_ROLE_SET.has(value as MediaRole)

const isLegacyBlock = (value: unknown): value is JournalStoryUpdate => {
  if (!isRecord(value)) {
    return false
  }
  return (
    value.fragment_type === 'block' ||
    Array.isArray(value.actions) ||
    Array.isArray(value.dialog) ||
    typeof value.text === 'string' ||
    typeof value.title === 'string'
  )
}

const normalizeFragmentStream = (fragments: unknown[]): JournalStoryUpdate[] => {
  const normalized: JournalStoryUpdate[] = []

  let current: JournalStoryUpdate | null = null
  let counter = 0
  const openBlock = () => {
    if (current === null) {
      counter += 1
      current = {
        uid: `story-${counter}`,
        text: '',
        actions: [],
        media: [],
      }
    }
    return current
  }
  const closeBlock = () => {
    if (current === null) {
      return
    }
    if (
      current.text ||
      (current.actions && current.actions.length > 0) ||
      (current.media && current.media.length > 0)
    ) {
      normalized.push(current)
    }
    current = null
  }

  for (const fragment of fragments) {
    if (!isRecord(fragment)) {
      continue
    }

    const kind = String(fragment.fragment_type ?? '')
    if (kind === 'block' && isLegacyBlock(fragment)) {
      closeBlock()
      normalized.push(fragment)
      continue
    }

    if (kind === 'content') {
      const block = openBlock()
      const content = typeof fragment.content === 'string' ? fragment.content : ''
      block.text = block.text ? `${block.text}\n${content}` : content
      if (fragment.uid) {
        block.uid = String(fragment.uid)
      }
      continue
    }

    if (kind === 'choice') {
      const block = openBlock()
      if (fragment.uid) {
        block.uid = String(fragment.uid)
      }
      const edgeId = fragment.edge_id ?? fragment.uid
      if (!edgeId) {
        continue
      }
      const text = String(fragment.text ?? fragment.label ?? 'Continue')
      const actions = block.actions ? [...block.actions] : []
      actions.push({ uid: String(edgeId), text } as JournalAction)
      block.actions = actions
      continue
    }

    if (kind === 'media') {
      const block = openBlock()
      if (fragment.uid) {
        block.uid = String(fragment.uid)
      }
      const payload = isRecord(fragment.payload) ? fragment.payload : {}
      const rawUrl = fragment.url ?? fragment.src ?? payload.url ?? payload.src
      const url = typeof rawUrl === 'string' ? rawUrl : undefined
      const rawData = fragment.data ?? payload.data
      const roleValue = fragment.media_role ?? payload.media_role
      const role = isMediaRole(roleValue) ? roleValue : 'narrative_im'

      if (url === undefined && rawData === undefined) {
        continue
      }

      const media = block.media ? [...block.media] : []
      media.push({
        media_role: role,
        ...(url ? { url } : {}),
        ...(rawData !== undefined ? { data: rawData } : {}),
      })
      block.media = media
      continue
    }
  }

  closeBlock()
  return normalized
}

const normalizePayload = (payload: unknown): JournalStoryUpdate[] => {
  if (Array.isArray(payload)) {
    if (payload.every((item) => isLegacyBlock(item))) {
      return payload as JournalStoryUpdate[]
    }
    return normalizeFragmentStream(payload)
  }

  if (!isRecord(payload)) {
    return []
  }

  if (Array.isArray(payload.fragments)) {
    const fragments = payload.fragments
    if (fragments.every((item) => isLegacyBlock(item))) {
      return fragments as JournalStoryUpdate[]
    }
    return normalizeFragmentStream(fragments)
  }

  const envelope = payload.envelope
  if (isRecord(envelope) && Array.isArray(envelope.fragments)) {
    return normalizeFragmentStream(envelope.fragments)
  }

  return []
}

const handleResponse = async (payload: JournalStoryUpdate[]) => {
  if (!Array.isArray(payload) || payload.length === 0) {
    return
  }

  if (payload[0]?.label) {
    blocks.value = []
    blockCounter.value = 0
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
    loading.value = true
    error.value = null
    const response = await $http.value.get<unknown>(`${storyRoutePrefix}/update`)
    await handleResponse(normalizePayload(response.data))
  } catch (err) {
    console.error('Failed to fetch initial story.', err)
    error.value = 'Failed to load story. Please refresh the page.'
  } finally {
    loading.value = false
  }
}

onMounted(fetchInitialBlocks)

const doAction = async (
  _block: JournalStoryUpdate,
  actionUid: string,
  payload?: unknown,
) => {
  try {
    loading.value = true
    error.value = null
    const response = await $http.value.post<unknown>(`${storyRoutePrefix}/do`, {
      choice_id: actionUid,
      payload,
    })
    await handleResponse(normalizePayload(response.data))
  } catch (err) {
    console.error('Failed to execute action.', err)
    error.value = 'Failed to execute action. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <v-progress-linear
      v-if="loading"
      class="mb-4"
      color="primary"
      indeterminate
      data-testid="storyflow-progress"
    />

    <v-alert
      v-if="error"
      class="mb-4"
      type="error"
      variant="tonal"
      closable
      @click:close="error = null"
    >
      {{ error }}
    </v-alert>

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
