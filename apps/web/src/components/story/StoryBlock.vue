<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import ContentFragmentView from './ContentFragmentView.vue'
import GroupFragmentView from './GroupFragmentView.vue'
import KvFragmentView from './KvFragmentView.vue'
import MediaFragmentView from './MediaFragmentView.vue'
import RollFragmentView from './RollFragmentView.vue'
import StoryAction from './StoryAction.vue'
import PieceFragmentView from './PieceFragmentView.vue'
import UnknownFragmentFallback from './UnknownFragmentFallback.vue'
import type { ChoiceStoryFragment, StoryFragment, StorySceneModel } from '@/types'
import { useGlobal } from '@/composables/globals'
import {
  isChoiceFragment,
  isGroupFragment,
  isMediaFragment,
  isPieceFragment,
  isRollFragment,
} from './fragmentUtils'

const props = defineProps<{
  scene: StorySceneModel
  fragments: Record<string, StoryFragment>
  metadata?: Record<string, unknown>
  disabled?: boolean
}>()

const emit = defineEmits<{
  doAction: [edgeId: string, payload?: unknown]
}>()

const { $debug, $verbose } = useGlobal()
const sceneRoot = ref<HTMLElement | null>(null)

const sceneMembers = computed(() =>
  props.scene.memberIds
    .map((id) => props.fragments[id])
    .filter((fragment): fragment is StoryFragment => Boolean(fragment)),
)
const choices = computed<ChoiceStoryFragment[]>(() =>
  sceneMembers.value.filter(isChoiceFragment),
)
const flowMembers = computed(() =>
  sceneMembers.value.filter(
    (fragment) =>
      !isChoiceFragment(fragment) &&
      fragment.fragment_type !== 'update' &&
      fragment.fragment_type !== 'delete',
  ),
)
const debugEnabled = computed(() => $debug.value && $verbose.value)

const handleAction = (edgeId: string, payload?: unknown) => {
  emit('doAction', edgeId, payload)
}

const textControlHasFocus = (event: KeyboardEvent): boolean => {
  const target = event.target instanceof HTMLElement ? event.target : document.activeElement
  return (
    target instanceof HTMLElement &&
    (target.matches('input, select, textarea') ||
      target.closest('[contenteditable]:not([contenteditable="false"])') !== null)
  )
}

const handleChoiceKey = (event: KeyboardEvent) => {
  if (
    props.disabled ||
    event.altKey ||
    event.ctrlKey ||
    event.metaKey ||
    textControlHasFocus(event)
  ) {
    return
  }
  const key = event.key.toLowerCase()
  const button = Array.from(
    sceneRoot.value?.querySelectorAll<HTMLButtonElement>('button[data-hotkey]:not(:disabled)') ?? [],
  ).find((candidate) => candidate.dataset.hotkey?.toLowerCase() === key)
  if (button) {
    event.preventDefault()
    button.click()
  }
}

onMounted(() => window.addEventListener('keydown', handleChoiceKey))
onBeforeUnmount(() => window.removeEventListener('keydown', handleChoiceKey))
</script>

<template>
  <div ref="sceneRoot">
    <v-card class="mb-4 story-scene" data-testid="story-scene">
      <v-card-item>
        <div v-for="fragment in flowMembers" :key="fragment.uid" class="fragment-row">
          <ContentFragmentView
            v-if="fragment.fragment_type === 'content'"
            :fragment="fragment"
          />

          <MediaFragmentView v-else-if="isMediaFragment(fragment)" :fragment="fragment" />

          <GroupFragmentView
            v-else-if="isGroupFragment(fragment)"
            :group="fragment"
            :fragments="fragments"
          />

          <KvFragmentView v-else-if="fragment.fragment_type === 'kv'" :fragment="fragment" />

          <PieceFragmentView v-else-if="isPieceFragment(fragment)" :fragment="fragment" />

          <RollFragmentView v-else-if="isRollFragment(fragment)" :fragment="fragment" />

          <UnknownFragmentFallback v-else :fragment="fragment" />
        </div>

        <v-card-actions v-if="choices.length > 0" role="group" aria-label="choices">
          <v-row dense>
            <StoryAction
              v-for="(choice, index) in choices"
              :key="choice.uid"
              :choice="choice"
              :position="index + 1"
              :fragments="fragments"
              :disabled="disabled"
              @doAction="handleAction"
            />
          </v-row>
        </v-card-actions>
      </v-card-item>

      <v-card-item v-if="debugEnabled">
        <v-card border>
          <v-card-text class="text-caption">
            Scene: {{ scene }}
          </v-card-text>
        </v-card>
      </v-card-item>
    </v-card>
  </div>
</template>

<style scoped>
.story-scene {
  overflow: hidden;
}

.fragment-row + .fragment-row {
  margin-top: 10px;
}
</style>
