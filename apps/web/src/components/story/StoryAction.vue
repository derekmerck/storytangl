<script setup lang="ts">
import { computed } from 'vue'

import type { JournalAction } from '@/types'

/**
 * StoryAction - renders a clickable story choice using the Vuetify button API.
 *
 * @emits doAction - emitted when the user selects the action. Payload includes the action uid
 *   and optional passback data used by the backend to resume context.
 *
 * @example
 * ```vue
 * <StoryAction
 *   :action="{ uid: 'choice1', text: 'Go north' }"
 *   @doAction="handleAction"
 * />
 * ```
 */
const props = defineProps<{
  action: JournalAction
}>()

const emit = defineEmits<{
  /**
   * Triggered when the action button is clicked.
   */
  doAction: [uid: string, passback?: unknown]
}>()

const iconName = computed(() => {
  const icon = props.action.icon
  if (!icon) {
    return undefined
  }

  return icon.startsWith('mdi-') ? icon : `mdi-${icon}`
})

const buttonStyle = computed<Record<string, string | number> | undefined>(() => {
  const styleSource = props.action.style ?? props.action.style_dict
  if (!styleSource) {
    return undefined
  }

  const entries = Object.entries(styleSource).filter(([, value]) => {
    return typeof value === 'string' || typeof value === 'number'
  }) as Array<[string, string | number]>

  return entries.length ? Object.fromEntries(entries) : undefined
})

const handleClick = () => {
  emit('doAction', props.action.uid, props.action.passback)
}
</script>

<template>
  <v-col cols="12" class="py-1">
    <v-btn
      class="ma-1"
      variant="outlined"
      color="primary"
      size="large"
      :style="buttonStyle"
      @click="handleClick"
    >
      <v-icon v-if="iconName" :icon="iconName" start />
      {{ action.text }}
    </v-btn>
  </v-col>
</template>
