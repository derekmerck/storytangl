<script setup lang="ts">
import { computed } from 'vue'

import { useGlobal } from '@/composables/globals'
import type {
  AttributedStoryFragment,
  GroupStoryFragment,
  MediaStoryFragment,
  StoryFragment,
} from '@/types'
import { fragmentText, isMediaFragment, mediaContentUrl } from './fragmentUtils'
import { mediaRole } from './fragmentViewUtils'
import MediaFragmentView from './MediaFragmentView.vue'
import UnknownFragmentFallback from './UnknownFragmentFallback.vue'

type DialogLine = {
  line: AttributedStoryFragment
  media: MediaStoryFragment[]
}

const props = defineProps<{
  group: GroupStoryFragment
  fragments: Record<string, StoryFragment>
}>()

const { remapURL } = useGlobal()

const groupType = computed(() =>
  props.group.fragment_type === 'dialog' ? 'dialog' : props.group.group_type,
)
const groupMembers = computed(() =>
  props.group.member_ids
    .map((id) => props.fragments[id])
    .filter((fragment): fragment is StoryFragment => Boolean(fragment)),
)
const dialogLines = computed<DialogLine[]>(() => {
  const lines: DialogLine[] = []

  for (const member of groupMembers.value) {
    if (member.fragment_type === 'attributed') {
      lines.push({ line: member as AttributedStoryFragment, media: [] })
      continue
    }
    if (isMediaFragment(member) && lines.length > 0) {
      lines[lines.length - 1]!.media.push(member)
    }
  }

  return lines
})

const mediaUrl = (fragment: MediaStoryFragment): string | undefined => {
  const url = mediaContentUrl(fragment)
  return url ? remapURL(url) : undefined
}

const avatarMedia = (media: MediaStoryFragment[]): MediaStoryFragment | undefined =>
  media.find((item) => mediaRole(item) === 'avatar_im')
</script>

<template>
  <div class="group-fragment">
    <div v-if="groupType === 'dialog'" class="dialog-group" aria-live="polite">
      <div
        v-for="dialog in dialogLines"
        :key="dialog.line.uid"
        class="dialog-line"
      >
        <v-avatar v-if="avatarMedia(dialog.media)" size="48">
          <img
            :src="mediaUrl(avatarMedia(dialog.media)!)"
            alt=""
            class="w-100 h-100 object-cover"
          />
        </v-avatar>
        <div class="dialog-body">
          <div class="dialog-speaker">
            {{ dialog.line.who }}
            <span v-if="dialog.line.how">({{ dialog.line.how }})</span>
          </div>
          <div>{{ fragmentText(dialog.line.content) }}</div>
          <div
            v-for="media in dialog.media.filter((item) => mediaRole(item) !== 'avatar_im')"
            :key="media.uid"
            class="dialog-media"
          >
            <MediaFragmentView :fragment="media" compact />
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="groupType === 'status_sidecar'" class="kv-strip">
      <span v-for="member in groupMembers" :key="member.uid">
        {{ member.fragment_type }}
      </span>
    </div>

    <div v-else class="unknown-group">
      <div class="fragment-fallback-label">{{ groupType ?? 'group' }}</div>
      <UnknownFragmentFallback
        v-for="member in groupMembers"
        :key="member.uid"
        :fragment="member"
      />
    </div>
  </div>
</template>

<style scoped>
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

.unknown-group {
  border: 1px dashed rgba(var(--v-theme-on-surface), 0.32);
  border-radius: 6px;
  color: rgb(var(--v-theme-on-surface-variant));
  font-family: monospace;
  font-size: 0.82rem;
  margin: 8px 16px;
  padding: 10px 12px;
}

.unknown-group :deep(.fragment-fallback) {
  margin: 8px 0 0;
}

.fragment-fallback-label {
  color: rgb(var(--v-theme-primary));
  font-weight: 700;
  margin-right: 6px;
}
</style>
