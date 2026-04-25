<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'

import StoryBlock from './StoryBlock.vue'
import type {
  ControlStoryFragment,
  GroupStoryFragment,
  RuntimeEnvelope,
  StoryFragment,
  StorySceneModel,
  UserEventStoryFragment,
} from '@/types'
import { useGlobal } from '@/composables/globals'
import {
  fragmentRefId,
  fragmentText,
  isControlFragment,
  isGroupFragment,
  isRecord,
  isUserEventFragment,
  normalizeEnvelope,
} from './fragmentUtils'

const { $http, $debug, $verbose } = useGlobal()
const storyRoutePrefix = import.meta.env.VITE_STORY_ROUTE_PREFIX || '/story'

const fragmentRegistry = ref<Record<string, StoryFragment>>({})
const scenes = ref<StorySceneModel[]>([])
const userEvents = ref<UserEventStoryFragment[]>([])
const sceneRefs = ref<InstanceType<typeof StoryBlock>[]>([])
const sceneCounter = ref(0)
const loading = ref(false)
const error = ref<string | null>(null)

const debugEnabled = computed(() => $debug.value && $verbose.value)

const isSceneGroup = (fragment: StoryFragment): fragment is GroupStoryFragment =>
  isGroupFragment(fragment) && fragment.group_type === 'scene'

const visibleFragmentIds = (fragments: StoryFragment[]): string[] =>
  fragments
    .filter((fragment) => !isControlFragment(fragment) && !isUserEventFragment(fragment))
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

  if (groups.length > 0) {
    return groups.map((group) => {
      sceneCounter.value += 1
      return {
        key: `${group.uid}-${sceneCounter.value}`,
        uid: group.uid,
        memberIds: [...group.member_ids],
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
    },
  ]
}

const applyEnvelope = async (envelope: RuntimeEnvelope) => {
  const nextRegistry = { ...fragmentRegistry.value }
  const renderFragments: StoryFragment[] = []
  const eventFragments: UserEventStoryFragment[] = []

  for (const fragment of envelope.fragments) {
    if (isControlFragment(fragment)) {
      applyControlFragment(nextRegistry, fragment)
      continue
    }

    nextRegistry[fragment.uid] = fragment
    renderFragments.push(fragment)

    if (isUserEventFragment(fragment)) {
      eventFragments.push(fragment as UserEventStoryFragment)
    }
  }

  fragmentRegistry.value = nextRegistry
  userEvents.value.push(...eventFragments)

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

const doAction = async (actionUid: string, payload?: unknown) => {
  try {
    loading.value = true
    error.value = null
    const response = await $http.value.post<unknown>(`${storyRoutePrefix}/do`, {
      choice_id: actionUid,
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
      v-for="event in userEvents"
      :key="event.uid"
      class="mb-3"
      data-testid="user-event"
      role="status"
      aria-live="polite"
    >
      <v-alert density="compact" type="info" variant="tonal">
        <strong v-if="event.event_type">{{ event.event_type }}:</strong>
        {{ fragmentText(event.content) }}
      </v-alert>
    </div>

    <StoryBlock
      v-for="scene in scenes"
      :key="scene.key"
      ref="sceneRefs"
      :scene="scene"
      :fragments="fragmentRegistry"
      :disabled="loading"
      @doAction="doAction"
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
