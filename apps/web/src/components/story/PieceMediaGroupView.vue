<script setup lang="ts">
import { computed } from 'vue'

import type {
  GroupStoryFragment,
  MediaStoryFragment,
  PieceStoryFragment,
  StoryFragment,
} from '@/types'
import { isMediaFragment, isPieceFragment } from './fragmentUtils'
import MediaFragmentView from './MediaFragmentView.vue'
import PieceFragmentView from './PieceFragmentView.vue'

const props = defineProps<{
  group: GroupStoryFragment
  fragments: Record<string, StoryFragment>
}>()

const members = computed(() =>
  props.group.member_ids
    .map((id) => props.fragments[id])
    .filter((fragment): fragment is StoryFragment => Boolean(fragment)),
)
const associatedPiece = computed<PieceStoryFragment | undefined>(() =>
  members.value.find(isPieceFragment),
)
const associatedMedia = computed<MediaStoryFragment[]>(() =>
  members.value.filter(isMediaFragment),
)
</script>

<template>
  <section class="piece-media-group d-flex flex-wrap align-start ga-2">
    <PieceFragmentView v-if="associatedPiece" :fragment="associatedPiece" />
    <MediaFragmentView
      v-for="media in associatedMedia"
      :key="media.uid"
      :fragment="media"
      compact
    />
  </section>
</template>
