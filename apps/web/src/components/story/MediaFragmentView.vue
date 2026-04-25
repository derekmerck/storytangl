<script setup lang="ts">
import { computed } from 'vue'

import { useGlobal } from '@/composables/globals'
import type { MediaStoryFragment } from '@/types'
import { fragmentText, mediaContentUrl } from './fragmentUtils'
import { hasLandscapeShape, isPendingMedia, mediaRole } from './fragmentViewUtils'

const props = defineProps<{
  fragment: MediaStoryFragment
  compact?: boolean
}>()

const { remapURL } = useGlobal()

const role = computed(() => mediaRole(props.fragment))
const url = computed(() => {
  const value = mediaContentUrl(props.fragment)
  return value ? remapURL(value) : undefined
})
const placeholderClasses = computed(() => [
  'media-placeholder',
  { 'media-placeholder--small': props.compact },
])
</script>

<template>
  <div :class="['media-frame', { 'media-frame--compact': compact }]">
    <div
      v-if="isPendingMedia(fragment)"
      :class="placeholderClasses"
      data-testid="pending-media"
    >
      <span>{{ role }}</span>
      <code>{{ fragmentText(fragment.content) }}</code>
    </div>

    <audio
      v-else-if="role.includes('audio') || role.includes('music') || role.includes('sfx')"
      :src="url"
      controls
    />

    <video v-else-if="role.includes('video')" :src="url" controls />

    <v-parallax
      v-else-if="hasLandscapeShape(fragment)"
      :src="url"
      cover
      height="42vh"
      scale="0.5"
    />

    <v-img
      v-else
      :src="url"
      :alt="fragment.text ?? role"
      class="story-image"
      cover
    />
  </div>
</template>

<style scoped>
.media-frame {
  margin: 8px 16px;
}

.media-frame--compact {
  margin: 0;
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
</style>
