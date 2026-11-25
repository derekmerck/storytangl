<script setup lang="ts">
import { computed } from 'vue'

import type {
  AttributedStoryFragment,
  GroupStoryFragment,
  MediaStoryFragment,
  StoryFragment,
} from '@/types'
import AttributedLineView from './AttributedLineView.vue'
import { isAttributedFragment, isMediaFragment } from './fragmentUtils'
import PieceMediaGroupView from './PieceMediaGroupView.vue'
import UnknownFragmentFallback from './UnknownFragmentFallback.vue'
import ZoneFragmentView from './ZoneFragmentView.vue'

type DialogLine = {
  line: AttributedStoryFragment
  media: MediaStoryFragment[]
}

const props = defineProps<{
  group: GroupStoryFragment
  fragments: Record<string, StoryFragment>
}>()

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
    if (isAttributedFragment(member)) {
      lines.push({ line: member, media: [] })
      continue
    }
    if (isMediaFragment(member) && lines.length > 0) {
      lines[lines.length - 1]!.media.push(member)
    }
  }

  return lines
})

</script>

<template>
  <div class="group-fragment">
    <div v-if="groupType === 'dialog'" class="dialog-group" aria-live="polite">
      <AttributedLineView
        v-for="dialog in dialogLines"
        :key="dialog.line.uid"
        :line="dialog.line"
        :media="dialog.media"
      />
    </div>

    <ZoneFragmentView
      v-else-if="groupType === 'zone'"
      :group="group"
      :fragments="fragments"
    />

    <PieceMediaGroupView
      v-else-if="groupType === 'piece_media'"
      :group="group"
      :fragments="fragments"
    />

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
