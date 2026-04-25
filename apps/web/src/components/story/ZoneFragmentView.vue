<script setup lang="ts">
import { computed } from 'vue'

import type { GroupStoryFragment, StoryFragment } from '@/types'
import { isTokenFragment } from './fragmentUtils'
import TokenFragmentView from './TokenFragmentView.vue'
import UnknownFragmentFallback from './UnknownFragmentFallback.vue'

const props = defineProps<{
  group: GroupStoryFragment
  fragments: Record<string, StoryFragment>
}>()

const stringValue = (value: unknown): string | undefined =>
  typeof value === 'string' && value ? value : undefined

const readableValue = (value: string): string => value.replace(/_/g, ' ')

const zoneLabel = computed(() => {
  const hints = props.group.hints ?? props.group.presentation_hints
  const role = stringValue(props.group.zone_role)
  return (
    stringValue(hints?.label_text) ??
    stringValue(props.group.label) ??
    (role ? readableValue(role) : undefined) ??
    props.group.uid
  )
})

const zoneRole = computed(() => {
  const role = stringValue(props.group.zone_role)
  return role ? readableValue(role) : 'zone'
})

const members = computed(() =>
  props.group.member_ids
    .map((id) => props.fragments[id])
    .filter((fragment): fragment is StoryFragment => Boolean(fragment)),
)
const tokenMembers = computed(() => members.value.filter(isTokenFragment))
const fallbackMembers = computed(() =>
  members.value.filter((member) => !isTokenFragment(member)),
)
</script>

<template>
  <section
    class="zone-fragment"
    data-testid="zone-fragment"
    :aria-label="`${zoneLabel} zone`"
  >
    <header class="zone-header">
      <span class="zone-label">{{ zoneLabel }}</span>
      <span class="zone-role">{{ zoneRole }}</span>
    </header>

    <div v-if="members.length > 0" class="zone-members" role="list">
      <TokenFragmentView
        v-for="member in tokenMembers"
        :key="member.uid"
        :fragment="member"
        role="listitem"
      />
      <UnknownFragmentFallback
        v-for="member in fallbackMembers"
        :key="member.uid"
        :fragment="member"
        role="listitem"
      />
    </div>

    <div v-else class="empty-zone" data-testid="empty-zone">Empty</div>
  </section>
</template>

<style scoped>
.zone-fragment {
  background: rgba(var(--v-theme-surface-variant), 0.22);
  border: 1px solid rgba(var(--v-theme-on-surface), 0.16);
  border-radius: 6px;
  margin: 8px 16px;
  padding: 10px 12px 12px;
}

.zone-header {
  align-items: baseline;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}

.zone-label {
  font-weight: 800;
  overflow-wrap: anywhere;
}

.zone-role {
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 0.75rem;
  text-transform: uppercase;
}

.zone-members {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.zone-members :deep(.fragment-fallback) {
  margin: 0;
}

.empty-zone {
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 0.86rem;
}
</style>
