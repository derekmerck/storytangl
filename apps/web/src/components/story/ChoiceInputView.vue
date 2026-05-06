<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import type {
  ChoiceStoryFragment,
  GroupStoryFragment,
  StoryFragment,
  TokenStoryFragment,
} from '@/types'
import { fragmentText, isGroupFragment, isRecord, isTokenFragment } from './fragmentUtils'

type PayloadState = {
  valid: boolean
  payload?: unknown
  message?: string
}

type Validator = {
  kind?: unknown
  min?: unknown
  max?: unknown
  pattern?: unknown
  flags?: unknown
  message?: unknown
  values?: unknown
  case_sensitive?: unknown
}

type PreparedValidator = Validator & {
  regex?: RegExp
}

const props = defineProps<{
  choice: ChoiceStoryFragment
  fragments: Record<string, StoryFragment>
  disabled?: boolean
}>()

const emit = defineEmits<{
  payloadChange: [payload: unknown, valid: boolean]
  commit: []
}>()

const inputValue = ref('')
const selectedTokenIds = ref<string[]>([])

const stringValue = (value: unknown): string | undefined =>
  typeof value === 'string' && value ? value : undefined

const numericValue = (value: unknown): number | undefined =>
  typeof value === 'number' && Number.isFinite(value) ? value : undefined

const accepts = computed(() => props.choice.accepts ?? {})

const acceptsKind = computed(() => {
  const kind = accepts.value.kind
  if (typeof kind === 'string' && kind) {
    return kind
  }
  const input = accepts.value.input
  if (typeof input !== 'string') {
    return 'pick'
  }
  return ['number', 'integer', 'quantity'].includes(input) ? 'quantity' : 'text'
})
const hasExplicitKind = computed(() => typeof accepts.value.kind === 'string')

const rendersInput = computed(() => ['text', 'quantity', 'tokens'].includes(acceptsKind.value))
const inputLabel = computed(() => props.choice.text)
const placeholder = computed(() => stringValue(accepts.value.placeholder) ?? '')
const minValue = computed(() => numericValue(accepts.value.min))
const maxValue = computed(() => numericValue(accepts.value.max))
const stepValue = computed(() => numericValue(accepts.value.step) ?? 1)
const unitLabel = computed(() => stringValue(accepts.value.unit))
const required = computed(() => accepts.value.required !== false)

const validators = computed<Validator[]>(() =>
  Array.isArray(accepts.value.validators) ? accepts.value.validators : [],
)
const preparedValidators = computed<PreparedValidator[]>(() =>
  validators.value.map((validator) => {
    if (validator.kind !== 'regex' || typeof validator.pattern !== 'string') {
      return validator
    }
    const flags = typeof validator.flags === 'string' ? validator.flags : undefined
    try {
      return { ...validator, regex: new RegExp(validator.pattern, flags) }
    } catch {
      return validator
    }
  }),
)

const payloadKey = computed(() => {
  const payloadType = accepts.value.payload_type
  return typeof payloadType === 'string' && payloadType ? payloadType : undefined
})

const targetZoneRef = computed(() => {
  const constraints = accepts.value.constraints
  if (!isRecord(constraints)) {
    return undefined
  }
  return stringValue(constraints.target_zone_ref)
})

const targetZone = computed<GroupStoryFragment | undefined>(() => {
  const ref = targetZoneRef.value
  if (!ref) {
    return undefined
  }
  const fragment = props.fragments[ref]
  return fragment && isGroupFragment(fragment) ? fragment : undefined
})

const tokensByTokenId = computed(() => {
  const tokens = new Map<string, TokenStoryFragment>()
  for (const fragment of Object.values(props.fragments)) {
    if (isTokenFragment(fragment) && fragment.token_id) {
      tokens.set(fragment.token_id, fragment)
    }
  }
  return tokens
})

const tokenByMemberId = (memberId: string): TokenStoryFragment | undefined => {
  const fragment = props.fragments[memberId]
  if (fragment && isTokenFragment(fragment)) {
    return fragment
  }
  return tokensByTokenId.value.get(memberId)
}

const candidateTokens = computed<TokenStoryFragment[]>(() =>
  targetZone.value?.member_ids
    .map(tokenByMemberId)
    .filter((fragment): fragment is TokenStoryFragment => Boolean(fragment)) ?? [],
)

const tokenLabel = (token: TokenStoryFragment): string => {
  const hints = token.hints ?? token.presentation_hints
  const content = fragmentText(token.content)
  return (
    stringValue(hints?.label_text) ??
    stringValue(token.label) ??
    (content ? content : undefined) ??
    stringValue(token.token_id) ??
    token.uid
  )
}

const tokenPayloadId = (token: TokenStoryFragment): string => token.token_id ?? token.uid
const candidateTokenPayloadIds = computed(() => candidateTokens.value.map(tokenPayloadId))

const validateText = (value: string): string | undefined => {
  if (required.value && value.trim() === '') {
    return 'Required'
  }
  for (const validator of preparedValidators.value) {
    if (validator.kind === 'length') {
      const min = numericValue(validator.min)
      const max = numericValue(validator.max)
      if (min !== undefined && value.length < min) {
        return `Use at least ${min} characters`
      }
      if (max !== undefined && value.length > max) {
        return `Use at most ${max} characters`
      }
    }
    if (validator.kind === 'regex' && validator.regex) {
      validator.regex.lastIndex = 0
      if (!validator.regex.test(value)) {
        return stringValue(validator.message) ?? 'Does not match the expected pattern'
      }
    }
    if (validator.kind === 'enum' && Array.isArray(validator.values)) {
      const values = validator.values.filter(
        (item): item is string => typeof item === 'string',
      )
      const compareValue = validator.case_sensitive === true ? value : value.toLowerCase()
      const compareValues = validator.case_sensitive === true
        ? values
        : values.map((item) => item.toLowerCase())
      if (!compareValues.includes(compareValue)) {
        return `Use one of: ${values.join(', ')}`
      }
    }
  }
  return undefined
}

const wrapPayload = (value: unknown): unknown => {
  if (!payloadKey.value) {
    return value
  }
  const keyed = { [payloadKey.value]: value }
  return isRecord(props.choice.payload) ? { ...props.choice.payload, ...keyed } : keyed
}

const textPayload = (): PayloadState => {
  const message = validateText(inputValue.value)
  if (message) {
    return { valid: false, message }
  }
  if (hasExplicitKind.value && !payloadKey.value) {
    return { valid: true, payload: { text: inputValue.value } }
  }
  return { valid: true, payload: wrapPayload(inputValue.value) }
}

const quantityPayload = (): PayloadState => {
  if (required.value && inputValue.value === '') {
    return { valid: false, message: 'Required' }
  }
  if (!required.value && inputValue.value === '') {
    return { valid: true, payload: props.choice.payload }
  }
  const quantity = Number(inputValue.value)
  if (!Number.isFinite(quantity) || !Number.isInteger(quantity)) {
    return { valid: false, message: 'Use a whole number' }
  }
  if (minValue.value !== undefined && quantity < minValue.value) {
    return { valid: false, message: `Minimum is ${minValue.value}` }
  }
  if (maxValue.value !== undefined && quantity > maxValue.value) {
    return { valid: false, message: `Maximum is ${maxValue.value}` }
  }
  if (hasExplicitKind.value && !payloadKey.value) {
    return { valid: true, payload: { quantity } }
  }
  return { valid: true, payload: wrapPayload(quantity) }
}

const tokenPayload = (): PayloadState => {
  const min = minValue.value ?? 1
  const max = maxValue.value ?? 1
  if (candidateTokens.value.length === 0) {
    return { valid: false, message: 'No valid targets' }
  }
  if (selectedTokenIds.value.length < min) {
    return { valid: false, message: min === max ? `Select ${min}` : `Select ${min}-${max}` }
  }
  if (selectedTokenIds.value.length > max) {
    return { valid: false, message: `Select at most ${max}` }
  }
  return { valid: true, payload: { token_ids: [...selectedTokenIds.value] } }
}

const payloadState = computed<PayloadState>(() => {
  if (acceptsKind.value === 'text') {
    return textPayload()
  }
  if (acceptsKind.value === 'quantity') {
    return quantityPayload()
  }
  if (acceptsKind.value === 'tokens') {
    return tokenPayload()
  }
  return { valid: true, payload: props.choice.payload }
})

const toggleToken = (token: TokenStoryFragment) => {
  if (props.disabled) {
    return
  }
  const id = tokenPayloadId(token)
  if (selectedTokenIds.value.includes(id)) {
    selectedTokenIds.value = selectedTokenIds.value.filter((selected) => selected !== id)
    return
  }

  const max = maxValue.value ?? 1
  if (max <= 1) {
    selectedTokenIds.value = [id]
    return
  }
  if (selectedTokenIds.value.length >= max) {
    return
  }
  selectedTokenIds.value = [...selectedTokenIds.value, id]
}

const handleTokenKeydown = (event: KeyboardEvent, token: TokenStoryFragment) => {
  if (props.disabled) {
    return
  }
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    toggleToken(token)
  }
}

watch(
  payloadState,
  (state) => emit('payloadChange', state.payload, state.valid),
  { immediate: true },
)

watch(
  [acceptsKind, targetZoneRef, candidateTokenPayloadIds],
  () => {
    inputValue.value = ''
    selectedTokenIds.value = []
  },
)
</script>

<template>
  <div v-if="rendersInput" class="choice-input-view" data-testid="choice-input-view">
    <v-text-field
      v-if="acceptsKind === 'text'"
      v-model="inputValue"
      class="choice-input"
      density="compact"
      hide-details
      variant="outlined"
      :aria-label="inputLabel"
      :disabled="disabled"
      :placeholder="placeholder"
      @keydown.enter.prevent="emit('commit')"
    />

    <v-text-field
      v-else-if="acceptsKind === 'quantity'"
      v-model="inputValue"
      class="choice-input choice-input--quantity"
      density="compact"
      hide-details
      variant="outlined"
      type="number"
      :aria-label="inputLabel"
      :disabled="disabled"
      :min="minValue"
      :max="maxValue"
      :step="stepValue"
      :placeholder="placeholder || unitLabel || ''"
      @keydown.enter.prevent="emit('commit')"
    >
      <template v-if="unitLabel" #append-inner>
        <span class="choice-input-unit">{{ unitLabel }}</span>
      </template>
    </v-text-field>

    <div v-else-if="acceptsKind === 'tokens'" class="choice-token-input">
      <div
        v-if="candidateTokens.length > 0"
        class="choice-token-list"
        role="listbox"
        :aria-label="inputLabel"
      >
        <div
          v-for="token in candidateTokens"
          :key="token.uid"
          class="choice-token-option"
          :class="{ 'choice-token-option--selected': selectedTokenIds.includes(tokenPayloadId(token)) }"
          role="option"
          :aria-selected="selectedTokenIds.includes(tokenPayloadId(token))"
          :aria-disabled="disabled ? 'true' : undefined"
          :data-token-id="tokenPayloadId(token)"
          :tabindex="disabled ? undefined : 0"
          @click="toggleToken(token)"
          @keydown="handleTokenKeydown($event, token)"
        >
          {{ tokenLabel(token) }}
        </div>
      </div>
      <div v-else class="choice-input-message">No valid targets</div>
    </div>

    <div
      v-if="payloadState.message"
      class="choice-input-message"
      data-testid="choice-input-message"
    >
      {{ payloadState.message }}
    </div>
  </div>
</template>

<style scoped>
.choice-input-view {
  display: grid;
  gap: 6px;
  max-width: min(100%, 520px);
}

.choice-input {
  max-width: 280px;
}

.choice-input--quantity {
  max-width: 180px;
}

.choice-input-unit {
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 0.78rem;
}

.choice-token-input {
  min-width: 0;
}

.choice-token-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.choice-token-option {
  background: rgba(var(--v-theme-surface), 0.86);
  border: 1px solid rgba(var(--v-theme-primary), 0.34);
  border-radius: 6px;
  color: rgb(var(--v-theme-on-surface));
  cursor: pointer;
  font: inherit;
  min-height: 34px;
  padding: 6px 9px;
}

.choice-token-option[aria-disabled='true'] {
  cursor: default;
  opacity: 0.6;
}

.choice-token-option--selected {
  background: rgba(var(--v-theme-primary), 0.16);
  border-color: rgb(var(--v-theme-primary));
}

.choice-input-message {
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 0.78rem;
  padding: 0 4px;
}
</style>
