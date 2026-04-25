<script setup lang="ts">
import { computed } from 'vue'

import StoryAction from './StoryAction.vue'
import type {
  AttributedStoryFragment,
  ChoiceStoryFragment,
  GroupStoryFragment,
  MediaStoryFragment,
  StoryFragment,
  StorySceneModel,
} from '@/types'
import { useGlobal } from '@/composables/globals'
import {
  fragmentText,
  isChoiceFragment,
  isGroupFragment,
  isMediaFragment,
  mediaContentUrl,
} from './fragmentUtils'

type DialogLine = {
  line: AttributedStoryFragment
  media: MediaStoryFragment[]
}

const props = defineProps<{
  scene: StorySceneModel
  fragments: Record<string, StoryFragment>
  disabled?: boolean
}>()

const emit = defineEmits<{
  doAction: [uid: string, payload?: unknown]
}>()

const { $debug, $verbose, remapURL } = useGlobal()

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

const groupType = (fragment: GroupStoryFragment) =>
  fragment.fragment_type === 'dialog' ? 'dialog' : fragment.group_type

const groupMembers = (group: GroupStoryFragment): StoryFragment[] =>
  group.member_ids
    .map((id) => props.fragments[id])
    .filter((fragment): fragment is StoryFragment => Boolean(fragment))

const dialogLines = (group: GroupStoryFragment): DialogLine[] => {
  const lines: DialogLine[] = []

  for (const member of groupMembers(group)) {
    if (member.fragment_type === 'attributed') {
      lines.push({ line: member as AttributedStoryFragment, media: [] })
      continue
    }
    if (isMediaFragment(member) && lines.length > 0) {
      lines[lines.length - 1]!.media.push(member)
    }
  }

  return lines
}

const mediaUrl = (fragment: MediaStoryFragment): string | undefined => {
  const url = mediaContentUrl(fragment)
  return url ? remapURL(url) : undefined
}

const mediaRole = (fragment: MediaStoryFragment): string =>
  typeof fragment.media_role === 'string' && fragment.media_role
    ? fragment.media_role
    : 'media'

const isPendingMedia = (fragment: MediaStoryFragment): boolean =>
  fragment.content_format === 'rit' || fragment.generation_status === 'pending'

const mediaShape = (fragment: MediaStoryFragment): string | undefined => {
  const shape = fragment.staging_hints?.media_shape
  if (typeof shape === 'string') {
    return shape
  }
  const orientation = fragment.orientation
  return typeof orientation === 'string' ? orientation : undefined
}

const hasLandscapeShape = (fragment: MediaStoryFragment): boolean =>
  ['landscape', 'banner', 'cover', 'bg'].includes(mediaShape(fragment) ?? '')

const kvItems = (fragment: StoryFragment): Array<[string, unknown]> => {
  if (fragment.fragment_type !== 'kv' || !Array.isArray(fragment.content)) {
    return []
  }
  return fragment.content.filter(
    (item): item is [string, unknown] =>
      Array.isArray(item) && typeof item[0] === 'string' && item.length >= 2,
  )
}

const contentClass = (fragment: StoryFragment): string[] => {
  const hints = fragment.hints ?? fragment.presentation_hints
  if (!hints || typeof hints !== 'object' || !('style_tags' in hints)) {
    return []
  }
  return Array.isArray(hints.style_tags)
    ? hints.style_tags.map((tag) => `story-style-${tag}`)
    : []
}

const handleAction = (uid: string, payload?: unknown) => {
  emit('doAction', uid, payload)
}
</script>

<template>
  <v-card class="mb-4 story-scene" data-testid="story-scene">
    <v-card-item>
      <div v-for="fragment in flowMembers" :key="fragment.uid" class="fragment-row">
        <v-card-text
          v-if="fragment.fragment_type === 'content'"
          :class="contentClass(fragment)"
          v-html="fragmentText(fragment.content)"
        />

        <div v-else-if="isMediaFragment(fragment)" class="media-frame">
          <div v-if="isPendingMedia(fragment)" class="media-placeholder" data-testid="pending-media">
            <span>{{ mediaRole(fragment) }}</span>
            <code>{{ fragmentText(fragment.content) }}</code>
          </div>

          <audio
            v-else-if="mediaRole(fragment).includes('audio') || mediaRole(fragment).includes('music') || mediaRole(fragment).includes('sfx')"
            :src="mediaUrl(fragment)"
            controls
          />

          <video
            v-else-if="mediaRole(fragment).includes('video')"
            :src="mediaUrl(fragment)"
            controls
          />

          <v-parallax
            v-else-if="hasLandscapeShape(fragment)"
            :src="mediaUrl(fragment)"
            cover
            height="42vh"
            scale="0.5"
          />

          <v-img
            v-else
            :src="mediaUrl(fragment)"
            :alt="fragment.text ?? mediaRole(fragment)"
            class="story-image"
            cover
          />
        </div>

        <div v-else-if="isGroupFragment(fragment)" class="group-fragment">
          <div v-if="groupType(fragment) === 'dialog'" class="dialog-group" aria-live="polite">
            <div
              v-for="dialog in dialogLines(fragment)"
              :key="dialog.line.uid"
              class="dialog-line"
            >
              <v-avatar v-if="dialog.media.some((item) => mediaRole(item) === 'avatar_im')" size="48">
                <img
                  :src="mediaUrl(dialog.media.find((item) => mediaRole(item) === 'avatar_im')!)"
                  alt=""
                  class="w-100 h-100 object-cover"
                />
              </v-avatar>
              <div class="dialog-body">
                <div class="dialog-speaker">
                  {{ dialog.line.who }}
                  <span v-if="dialog.line.how">({{ dialog.line.how }})</span>
                </div>
                <div v-html="fragmentText(dialog.line.content)" />
                <div
                  v-for="media in dialog.media.filter((item) => mediaRole(item) !== 'avatar_im')"
                  :key="media.uid"
                  class="dialog-media"
                >
                  <div
                    v-if="isPendingMedia(media)"
                    class="media-placeholder media-placeholder--small"
                    data-testid="pending-media"
                  >
                    <span>{{ mediaRole(media) }}</span>
                    <code>{{ fragmentText(media.content) }}</code>
                  </div>
                  <v-img v-else :src="mediaUrl(media)" :alt="media.text ?? mediaRole(media)" cover />
                </div>
              </div>
            </div>
          </div>

          <div v-else-if="groupType(fragment) === 'status_sidecar'" class="kv-strip">
            <span v-for="member in groupMembers(fragment)" :key="member.uid">
              {{ member.fragment_type }}
            </span>
          </div>

          <div v-else class="unknown-group">
            <div class="fragment-fallback-label">{{ groupType(fragment) ?? 'group' }}</div>
            <div
              v-for="member in groupMembers(fragment)"
              :key="member.uid"
              class="fragment-fallback"
            >
              {{ member.fragment_type }}: {{ fragmentText(member.content) }}
            </div>
          </div>
        </div>

        <div v-else-if="fragment.fragment_type === 'kv'" class="kv-strip" aria-label="scene status">
          <span v-for="item in kvItems(fragment)" :key="item[0]" class="kv-pair">
            <span>{{ item[0] }}</span>
            <b>{{ fragmentText(item[1]) }}</b>
          </span>
        </div>

        <div v-else class="fragment-fallback" data-testid="fragment-fallback">
          <span class="fragment-fallback-label">{{ fragment.fragment_type }}</span>
          {{ fragmentText(fragment.content) }}
        </div>
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

.media-frame {
  margin: 8px 16px;
}

.story-image {
  max-height: 70vh;
}

.media-placeholder {
  align-items: center;
  aspect-ratio: 16 / 9;
  background: rgba(var(--v-theme-surface-variant), 0.36);
  border: 1px dashed rgba(var(--v-theme-on-surface), 0.32);
  border-radius: 6px;
  color: rgb(var(--v-theme-on-surface-variant));
  display: flex;
  flex-direction: column;
  font-size: 0.82rem;
  gap: 4px;
  justify-content: center;
  min-height: 120px;
  padding: 16px;
}

.media-placeholder--small {
  min-height: 88px;
}

.dialog-group {
  border-left: 3px solid rgba(var(--v-theme-primary), 0.45);
  margin: 8px 16px;
  padding-left: 12px;
}

.dialog-line {
  align-items: flex-start;
  display: flex;
  gap: 12px;
  padding: 8px 0;
}

.dialog-body {
  min-width: 0;
}

.dialog-speaker {
  color: rgb(var(--v-theme-primary));
  font-size: 0.86rem;
  font-weight: 700;
  margin-bottom: 2px;
}

.dialog-speaker span {
  color: rgb(var(--v-theme-on-surface-variant));
  font-style: italic;
  font-weight: 400;
  margin-left: 4px;
}

.dialog-media {
  margin-top: 8px;
  max-width: 280px;
}

.kv-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 8px 16px;
}

.kv-pair {
  background: rgba(var(--v-theme-surface-variant), 0.6);
  border-radius: 5px;
  display: inline-flex;
  gap: 6px;
  padding: 4px 8px;
}

.fragment-fallback,
.unknown-group {
  border: 1px dashed rgba(var(--v-theme-on-surface), 0.32);
  border-radius: 6px;
  color: rgb(var(--v-theme-on-surface-variant));
  font-family: monospace;
  font-size: 0.82rem;
  margin: 8px 16px;
  padding: 10px 12px;
}

.fragment-fallback-label {
  color: rgb(var(--v-theme-primary));
  font-weight: 700;
  margin-right: 6px;
}
</style>
