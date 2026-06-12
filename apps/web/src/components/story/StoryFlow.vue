<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'

import CommandBar from './CommandBar.vue'
import StoryBlock from './StoryBlock.vue'
import type {
  ControlStoryFragment,
  GroupStoryFragment,
  RuntimeEnvelope,
  StoryFragment,
  StorySceneModel,
  UxEvent,
} from '@/types'
import { useGlobal } from '@/composables/globals'
import {
  fragmentRefId,
  isControlFragment,
  isGroupFragment,
  isRecord,
  normalizeEnvelope,
} from './fragmentUtils'

const { $http, $debug, $verbose } = useGlobal()
const storyRoutePrefix = import.meta.env.VITE_STORY_ROUTE_PREFIX || '/story'

const emit = defineEmits<{
  storyUpdate: [envelope: RuntimeEnvelope]
}>()

const fragmentRegistry = ref<Record<string, StoryFragment>>({})
const scenes = ref<StorySceneModel[]>([])
const inlineEvents = ref<UxEvent[]>([])
const interruptEvents = ref<UxEvent[]>([])
const currentMetadata = ref<Record<string, unknown>>({})
const sceneRefs = ref<InstanceType<typeof StoryBlock>[]>([])
const sceneCounter = ref(0)
const loading = ref(false)
const error = ref<string | null>(null)

const debugEnabled = computed(() => $debug.value && $verbose.value)
const commandGrammar = computed(() => {
  const grammar = currentMetadata.value.grammar
  return isRecord(grammar) ? grammar : {}
})

const isSceneGroup = (fragment: StoryFragment): fragment is GroupStoryFragment =>
  isGroupFragment(fragment) && fragment.group_type === 'scene'

const visibleFragmentIds = (fragments: StoryFragment[]): string[] =>
  fragments
    .filter((fragment) => !isControlFragment(fragment))
    .map((fragment) => fragment.uid)

const applyControlFragment = (
  registry: Record<string, StoryFragment>,
  fragment: ControlStoryFragment,
) => {
  const refId = fragmentRefId(fragment)
  if (!refId) {
    return
  }

  if (fragment.fragment_type === 'delete') {
    delete registry[refId]
    return
  }

  if (!isRecord(fragment.payload)) {
    return
  }

  const existing = registry[refId]
  registry[refId] = {
    ...(existing ?? { uid: refId, fragment_type: fragment.ref_type ?? fragment.reference_type ?? 'content' }),
    ...fragment.payload,
    uid: refId,
    fragment_type:
      typeof fragment.payload.fragment_type === 'string'
        ? fragment.payload.fragment_type
        : (existing?.fragment_type ?? fragment.ref_type ?? fragment.reference_type ?? 'content'),
  } as StoryFragment
}

const buildScenes = (envelope: RuntimeEnvelope, renderFragments: StoryFragment[]): StorySceneModel[] => {
  const sceneGroups = renderFragments.filter(isSceneGroup)
  const groups = sceneGroups.length > 0 ? sceneGroups : []
  const metadata = envelope.metadata ?? {}

  if (groups.length > 0) {
    return groups.map((group) => {
      sceneCounter.value += 1
      return {
        key: `${group.uid}-${sceneCounter.value}`,
        uid: group.uid,
        memberIds: [...group.member_ids],
        metadata,
      }
    })
  }

  const memberIds = visibleFragmentIds(renderFragments)
  if (memberIds.length === 0) {
    return []
  }

  sceneCounter.value += 1
  return [
    {
      key: `scene-${envelope.step ?? sceneCounter.value}-${sceneCounter.value}`,
      uid: `scene-${envelope.step ?? sceneCounter.value}`,
      memberIds,
      metadata,
    },
  ]
}

const applyEnvelope = async (envelope: RuntimeEnvelope) => {
  const nextRegistry = { ...fragmentRegistry.value }
  const renderFragments: StoryFragment[] = []
  const uxEvents = envelope.ux_events ?? []

  for (const fragment of envelope.fragments) {
    if (isControlFragment(fragment)) {
      applyControlFragment(nextRegistry, fragment)
      continue
    }

    nextRegistry[fragment.uid] = fragment
    renderFragments.push(fragment)
  }

  fragmentRegistry.value = nextRegistry
  currentMetadata.value = envelope.metadata ?? {}
  inlineEvents.value = uxEvents.filter((event) => event.presentation === 'inline')
  const nextInterruptEvents = [
    ...interruptEvents.value.filter((event) => event.replay),
    ...uxEvents.filter((event) => event.presentation === 'interrupt'),
  ]
  interruptEvents.value = [
    ...new Map(nextInterruptEvents.map((event) => [event.event_id, event])).values(),
  ]

  const newScenes = buildScenes(envelope, renderFragments)
  if (newScenes.length === 0) {
    return
  }

  const startingIndex = scenes.value.length
  scenes.value.push(...newScenes)

  await nextTick(() => {
    const target = sceneRefs.value[startingIndex]
    const element = target?.$el as HTMLElement | undefined
    element?.scrollIntoView({ behavior: startingIndex ? 'smooth' : 'auto' })
  })
}

const handlePayload = async (payload: unknown, fallbackPrefix: string) => {
  const envelope = normalizeEnvelope(payload, { fallbackPrefix })
  if (envelope === null) {
    return
  }
  await applyEnvelope(envelope)
  emit('storyUpdate', envelope)
}

const fetchInitialBlocks = async () => {
  try {
    loading.value = true
    error.value = null
    const response = await $http.value.get<unknown>(`${storyRoutePrefix}/update`)
    await handlePayload(response.data, 'initial-fragment')
  } catch (err) {
    console.error('Failed to fetch initial story.', err)
    error.value = 'Failed to load story. Please refresh the page.'
  } finally {
    loading.value = false
  }
}

onMounted(fetchInitialBlocks)

const doAction = async (edgeId: string, payload?: unknown) => {
  try {
    loading.value = true
    error.value = null
    const response = await $http.value.post<unknown>(`${storyRoutePrefix}/do`, {
      edge_id: edgeId,
      payload,
    })
    await handlePayload(response.data, `action-${scenes.value.length + 1}`)
  } catch (err) {
    console.error('Failed to execute action.', err)
    error.value = 'Failed to execute action. Please try again.'
  } finally {
    loading.value = false
  }
}

const doCommand = async (command: string) => {
  try {
    loading.value = true
    error.value = null
    const response = await $http.value.post<unknown>(`${storyRoutePrefix}/do`, {
      find_edge: {
        kind: 'command',
        command,
      },
    })
    await handlePayload(response.data, `command-${scenes.value.length + 1}`)
  } catch (err) {
    console.error('Failed to execute command.', err)
    error.value = 'Failed to execute command. Please try again.'
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

    <div
      v-for="event in interruptEvents"
      :key="event.event_id"
      class="mb-3"
      data-testid="interrupt-ux-event"
      role="alert"
    >
      <v-alert :type="event.severity" density="compact" variant="tonal">
        {{ event.message }}
      </v-alert>
    </div>

    <StoryBlock
      v-for="scene in scenes"
      :key="scene.key"
      ref="sceneRefs"
      :scene="scene"
      :fragments="fragmentRegistry"
      :metadata="scene.metadata"
      :disabled="loading"
      @doAction="doAction"
    />

    <CommandBar
      :grammar="commandGrammar"
      :events="inlineEvents"
      :disabled="loading"
      @submit="doCommand"
    />

    <v-card v-if="debugEnabled" class="mt-4">
      <v-card-item>
        <v-card border>
          <v-card-text class="text-caption">
            Scenes: {{ scenes }}
            Fragments: {{ fragmentRegistry }}
          </v-card-text>
        </v-card>
      </v-card-item>
    </v-card>
  </div>
</template>
