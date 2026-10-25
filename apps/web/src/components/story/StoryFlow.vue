<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { isAxiosError } from 'axios'

import CommandBar from './CommandBar.vue'
import StoryBlock from './StoryBlock.vue'
import type {
  GroupStoryFragment,
  GrammarHint,
  RuntimeEnvelope,
  RuntimeMetadata,
  StoryFragment,
  StorySceneModel,
  UxEvent,
} from '@/types'
import { useGlobal } from '@/composables/globals'
import {
  applyControlFragment,
  isControlFragment,
  isGroupFragment,
  isChoiceFragment,
  normalizeEnvelope,
} from './fragmentUtils'

const { $http, $debug, $verbose } = useGlobal()
const storyRoutePrefix = import.meta.env.VITE_STORY_ROUTE_PREFIX || '/story'

const emit = defineEmits<{
  storyUpdate: [envelope: RuntimeEnvelope]
  writePending: [pending: boolean]
  resynchronize: [message: string]
}>()
const props = defineProps<{ initialEnvelope: RuntimeEnvelope; activeChoiceIds: string[] }>()
const activeChoiceIds = ref([...props.activeChoiceIds])
const currentStep = ref(props.initialEnvelope.step)
let alive = true
onBeforeUnmount(() => {
  alive = false
})

const fragmentRegistry = ref<Record<string, StoryFragment>>({})
const scenes = ref<StorySceneModel[]>([])
const inlineEvents = ref<UxEvent[]>([])
const interruptEvents = ref<UxEvent[]>([])
const currentMetadata = ref<RuntimeMetadata>({})
const sceneRefs = ref<InstanceType<typeof StoryBlock>[]>([])
const sceneCounter = ref(0)
const loading = ref(false)

const debugEnabled = computed(() => $debug.value && $verbose.value)
const commandGrammar = computed<GrammarHint>(() => currentMetadata.value.grammar ?? {})

const isSceneGroup = (fragment: StoryFragment): fragment is GroupStoryFragment =>
  isGroupFragment(fragment) && fragment.group_type === 'scene'

const visibleFragmentIds = (fragments: StoryFragment[]): string[] =>
  fragments.filter((fragment) => !isControlFragment(fragment)).map((fragment) => fragment.uid)

const buildScenes = (
  envelope: RuntimeEnvelope,
  renderFragments: StoryFragment[]
): StorySceneModel[] => {
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
    throw new Error('Invalid runtime envelope')
  }
  if (envelope.step !== currentStep.value) {
    activeChoiceIds.value = envelope.fragments.filter(isChoiceFragment).map((item) => item.uid)
  }
  currentStep.value = envelope.step
  await applyEnvelope(envelope)
  if (alive) emit('storyUpdate', envelope)
}

onMounted(() => handlePayload(props.initialEnvelope, 'initial-fragment'))

const submit = async (request: Record<string, unknown>) => {
  if (loading.value) return
  loading.value = true
  emit('writePending', true)
  try {
    const response = await $http.value.post<unknown>(`${storyRoutePrefix}/do`, request)
    if (!alive) return
    await handlePayload(response.data, `action-${scenes.value.length + 1}`)
  } catch (err) {
    if (!alive) return
    console.error('Failed to execute action.', err)
    const detail = isAxiosError<{ detail?: string }>(err) ? err.response?.data?.detail : undefined
    emit('resynchronize', typeof detail === 'string' ? detail : 'The request failed.')
  } finally {
    if (alive) {
      loading.value = false
      emit('writePending', false)
    }
  }
}

const doAction = async (edgeId: string, payload?: unknown) => {
  const offered = activeChoiceIds.value.some((id) => {
    const choice = fragmentRegistry.value[id]
    return (
      choice && isChoiceFragment(choice) && choice.edge_id === edgeId && choice.available !== false
    )
  })
  if (offered) await submit({ edge_id: edgeId, payload })
}
const doCommand = (command: string) => submit({ find_edge: { kind: 'command', command } })
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
      :active-choice-ids="activeChoiceIds"
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
            Scenes: {{ scenes }} Fragments: {{ fragmentRegistry }}
          </v-card-text>
        </v-card>
      </v-card-item>
    </v-card>
  </div>
</template>
