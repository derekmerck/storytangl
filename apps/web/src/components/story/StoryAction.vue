<script setup lang="ts">
import { computed, ref } from 'vue'

import ChoiceInputView from './ChoiceInputView.vue'
import type { ChoiceStoryFragment, StoryFragment } from '@/types'
import { isRecord } from './fragmentUtils'

const props = defineProps<{
  choice: ChoiceStoryFragment
  fragments?: Record<string, StoryFragment>
  disabled?: boolean
}>()

const emit = defineEmits<{
  doAction: [edgeId: string, payload?: unknown]
}>()

const payloadValue = ref<unknown>(props.choice.payload)
const payloadValid = ref(true)

const choiceId = computed(() => props.choice.edge_id ?? props.choice.uid)
const available = computed(() => props.choice.available !== false && props.choice.active !== false)
const busy = computed(() => props.disabled === true)
const hotkey = computed(() => {
  const value = props.choice.ui_hints?.hotkey
  return typeof value === 'string' ? value : undefined
})
const iconName = computed(() => {
  const icon = props.choice.ui_hints?.icon ?? props.choice.icon
  if (typeof icon !== 'string' || !icon) {
    return undefined
  }
  return icon.startsWith('mdi-') ? icon : `mdi-${icon}`
})
const hasPayloadInput = computed(() => {
  if (!props.choice.accepts) {
    return false
  }
  const kind = props.choice.accepts.kind
  if (typeof kind === 'string' && ['text', 'quantity', 'tokens'].includes(kind)) {
    return true
  }
  return typeof props.choice.accepts.input === 'string'
})
const canCommit = computed(() => available.value && !busy.value && payloadValid.value)

const buttonStyle = computed<Record<string, string | number> | undefined>(() => {
  const styleSource = props.choice.style ?? props.choice.style_dict
  if (!isRecord(styleSource)) {
    return undefined
  }

  const entries = Object.entries(styleSource).filter(([, value]) => {
    return typeof value === 'string' || typeof value === 'number'
  }) as Array<[string, string | number]>

  return entries.length ? Object.fromEntries(entries) : undefined
})

const handlePayloadChange = (payload: unknown, valid: boolean) => {
  payloadValue.value = payload
  payloadValid.value = valid
}

const handleClick = () => {
  if (!canCommit.value) {
    return
  }
  emit('doAction', choiceId.value, payloadValue.value)
}
</script>

<template>
  <v-col cols="12" class="py-1">
    <div class="choice-row" :class="{ 'choice-row--locked': !available }">
      <v-btn
        class="ma-1 text-start choice-button"
        variant="outlined"
        color="primary"
        size="large"
        :style="buttonStyle"
        :aria-disabled="!canCommit"
        :data-hotkey="hotkey"
        @click="handleClick"
      >
        <span v-if="hotkey" class="choice-hotkey">{{ hotkey }}</span>
        <v-icon v-if="iconName" :icon="iconName" start />
        <span>{{ choice.text }}</span>
      </v-btn>

      <ChoiceInputView
        v-if="hasPayloadInput"
        :choice="choice"
        :fragments="fragments ?? {}"
        :disabled="!available || busy"
        @payload-change="handlePayloadChange"
        @commit="handleClick"
      />

      <div v-if="!available && choice.unavailable_reason" class="choice-reason">
        {{ choice.unavailable_reason }}
      </div>
    </div>
  </v-col>
</template>

<style scoped>
.choice-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 6px;
}

.choice-row--locked {
  opacity: 0.64;
}

.choice-button {
  min-height: 44px;
  white-space: normal;
  width: 100%;
}

.choice-hotkey {
  border: 1px solid currentColor;
  border-radius: 4px;
  font-size: 0.72rem;
  line-height: 1;
  margin-right: 8px;
  min-width: 22px;
  padding: 3px 5px;
  text-align: center;
}

.choice-reason {
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 0.78rem;
  padding: 0 8px 4px;
}
</style>
