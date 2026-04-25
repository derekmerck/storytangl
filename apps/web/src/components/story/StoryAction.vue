<script setup lang="ts">
import { computed, ref } from 'vue'

import type { ChoiceStoryFragment } from '@/types'
import { isRecord } from './fragmentUtils'

const props = defineProps<{
  choice: ChoiceStoryFragment
  disabled?: boolean
}>()

const emit = defineEmits<{
  doAction: [uid: string, payload?: unknown]
}>()

const inputValue = ref('')

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
const acceptsInput = computed(() => {
  const input = props.choice.accepts?.input ?? props.choice.accepts?.kind
  return typeof input === 'string' ? input : undefined
})
const hasFreeformInput = computed(() => Boolean(props.choice.accepts && acceptsInput.value))
const inputType = computed(() => {
  return acceptsInput.value === 'integer' || acceptsInput.value === 'quantity' ? 'number' : 'text'
})
const placeholder = computed(() => {
  const value = props.choice.accepts?.placeholder
  return typeof value === 'string' ? value : ''
})
const minValue = computed(() => {
  const value = props.choice.accepts?.min
  return typeof value === 'number' ? value : undefined
})
const maxValue = computed(() => {
  const value = props.choice.accepts?.max
  return typeof value === 'number' ? value : undefined
})

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

const coerceInputPayload = (): unknown => {
  if (!hasFreeformInput.value) {
    return props.choice.payload
  }

  let value: unknown = inputValue.value
  if (inputType.value === 'number') {
    const parsed = Number(inputValue.value)
    value = Number.isNaN(parsed) ? inputValue.value : parsed
  }

  const payloadType = props.choice.accepts?.payload_type
  if (typeof payloadType === 'string' && payloadType) {
    value = { [payloadType]: value }
  }

  if (isRecord(props.choice.payload) && isRecord(value)) {
    return { ...props.choice.payload, ...value }
  }
  return value
}

const handleClick = () => {
  if (!available.value || busy.value) {
    return
  }
  emit('doAction', choiceId.value, coerceInputPayload())
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
        :aria-disabled="!available || busy"
        :data-hotkey="hotkey"
        @click="handleClick"
      >
        <span v-if="hotkey" class="choice-hotkey">{{ hotkey }}</span>
        <v-icon v-if="iconName" :icon="iconName" start />
        <span>{{ choice.text }}</span>
      </v-btn>

      <v-text-field
        v-if="hasFreeformInput"
        v-model="inputValue"
        class="choice-input"
        density="compact"
        hide-details
        variant="outlined"
        :disabled="!available || busy"
        :type="inputType"
        :min="minValue"
        :max="maxValue"
        :placeholder="placeholder"
        @keydown.enter.prevent="handleClick"
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

.choice-input {
  max-width: 260px;
}

.choice-reason {
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 0.78rem;
  padding: 0 8px 4px;
}
</style>
