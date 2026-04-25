<script setup lang="ts">
import { computed } from 'vue'

import ContentFragmentView from './ContentFragmentView.vue'
import GroupFragmentView from './GroupFragmentView.vue'
import KvFragmentView from './KvFragmentView.vue'
import MediaFragmentView from './MediaFragmentView.vue'
import StoryAction from './StoryAction.vue'
import TokenFragmentView from './TokenFragmentView.vue'
import UnknownFragmentFallback from './UnknownFragmentFallback.vue'
import type { ChoiceStoryFragment, StoryFragment, StorySceneModel } from '@/types'
import { useGlobal } from '@/composables/globals'
import {
  isChoiceFragment,
  isGroupFragment,
  isMediaFragment,
  isTokenFragment,
} from './fragmentUtils'

const props = defineProps<{
  scene: StorySceneModel
  fragments: Record<string, StoryFragment>
  disabled?: boolean
}>()

const emit = defineEmits<{
  doAction: [uid: string, payload?: unknown]
}>()

const { $debug, $verbose } = useGlobal()

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
      fragment.fragment_type !== 'delete' &&
      fragment.fragment_type !== 'user_event',
  ),
)
const debugEnabled = computed(() => $debug.value && $verbose.value)

const handleAction = (uid: string, payload?: unknown) => {
  emit('doAction', uid, payload)
}
</script>

<template>
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

        <TokenFragmentView v-else-if="isTokenFragment(fragment)" :fragment="fragment" />

        <UnknownFragmentFallback v-else :fragment="fragment" />
      </div>

      <v-card-actions v-if="choices.length > 0" role="group" aria-label="choices">
        <v-row dense>
          <StoryAction
            v-for="choice in choices"
            :key="choice.uid"
            :choice="choice"
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
</template>

<style scoped>
.story-scene {
  overflow: hidden;
}

.fragment-row + .fragment-row {
  margin-top: 10px;
}
</style>
