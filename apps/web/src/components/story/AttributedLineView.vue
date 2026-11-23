<script setup lang="ts">
import { computed } from 'vue'

import { useGlobal } from '@/composables/globals'
import type { AttributedStoryFragment, MediaStoryFragment } from '@/types'
import { fragmentText, mediaContentUrl } from './fragmentUtils'
import { contentClass, mediaRole } from './fragmentViewUtils'
import MediaFragmentView from './MediaFragmentView.vue'

/**
 * One attributed line, standalone or a member of a dialog group: the speaker as
 * the service realized it (`who`), its manner (`how`), the prose, and any media
 * the group associated with the line. The one attribution path for both shapes.
 */
const props = defineProps<{
  line: AttributedStoryFragment
  media?: MediaStoryFragment[]
}>()

const { remapURL } = useGlobal()

const avatarUrl = computed(() => {
  const avatar = props.media?.find((item) => mediaRole(item) === 'avatar_im')
  const url = avatar && mediaContentUrl(avatar)
  return url ? remapURL(url) : undefined
})
const otherMedia = computed(
  () => props.media?.filter((item) => mediaRole(item) !== 'avatar_im') ?? []
)
</script>

<template>
  <div :class="['dialog-line', contentClass(line)]" data-testid="attributed-line">
    <v-avatar v-if="avatarUrl" size="48">
      <img :src="avatarUrl" alt="" class="w-100 h-100 object-cover" />
    </v-avatar>
    <div class="dialog-body">
      <div v-if="line.who" class="dialog-speaker">
        {{ line.who }}
        <span v-if="line.how">({{ line.how }})</span>
      </div>
      <div>{{ fragmentText(line.content) }}</div>
      <div v-for="item in otherMedia" :key="item.uid" class="dialog-media">
        <MediaFragmentView :fragment="item" compact />
      </div>
    </div>
  </div>
</template>

<style scoped>
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
</style>
