<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import type {
  ChoiceAccepts,
  ChoiceStoryFragment,
  GroupStoryFragment,
  StoryFragment,
  PieceStoryFragment,
} from '@/types'
import { fragmentText, isGroupFragment, isRecord, isPieceFragment } from './fragmentUtils'

defineOptions({ name: 'ChoiceInputView' })

type PayloadState = {
  valid: boolean
  payload?: unknown
  message?: string
}

type ComposePartInput = {
  role: string
  accepts: ChoiceAccepts
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

type CommandGrammar = {
  examples?: unknown
  placeholder?: unknown
}

const props = defineProps<{
  choice: ChoiceStoryFragment
  fragments: Record<string, StoryFragment>
  metadata?: Record<string, unknown>
  disabled?: boolean
}>()

const emit = defineEmits<{
  payloadChange: [payload: unknown, valid: boolean]
  commit: []
}>()

const inputValue = ref('')
const selectedPieceIds = ref<string[]>([])
const composePartStates = ref<Record<string, PayloadState>>({})

const stringValue = (value: unknown): string | undefined =>
  typeof value === 'string' && value ? value : undefined

const numericValue = (value: unknown): number | undefined =>
  typeof value === 'number' && Number.isFinite(value) ? value : undefined

const accepts = computed<Record<string, unknown>>(() =>
  props.choice.accepts ? (props.choice.accepts as unknown as Record<string, unknown>) : {},
)

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

const rendersInput = computed(() =>
  ['text', 'quantity', 'pieces', 'place', 'compose', 'raw_command'].includes(acceptsKind.value),
)
const inputLabel = computed(() => props.choice.text)
const commandGrammar = computed<CommandGrammar>(() => {
  const grammar = props.metadata?.grammar
  return isRecord(grammar) ? grammar : {}
})
const commandExamples = computed(() =>
  Array.isArray(commandGrammar.value.examples)
    ? commandGrammar.value.examples.filter(
        (example): example is string => typeof example === 'string' && example.length > 0,
      )
    : [],
)
const commandPlaceholder = computed(() => {
  if (acceptsKind.value !== 'raw_command') {
    return undefined
  }
  return (
    stringValue(commandGrammar.value.placeholder) ??
    (commandExamples.value.length > 0 ? `e.g. ${commandExamples.value[0]}` : 'Type a command')
  )
})
const placeholder = computed(() =>
  stringValue(accepts.value.placeholder) ?? commandPlaceholder.value ?? '',
)
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
    return stringValue(accepts.value.target_zone_ref)
  }
  return stringValue(accepts.value.target_zone_ref) ?? stringValue(constraints.target_zone_ref)
})

const sourceZoneRef = computed(() => {
  const constraints = accepts.value.constraints
  if (!isRecord(constraints)) {
    return stringValue(accepts.value.source_zone_ref)
  }
  return stringValue(accepts.value.source_zone_ref) ?? stringValue(constraints.source_zone_ref)
})

const composeParts = computed<ComposePartInput[]>(() => {
  const parts = accepts.value.parts
  if (!Array.isArray(parts)) {
    return []
  }
  return parts
    .filter(
      (part): part is Record<string, unknown> & { role: string; accepts: ChoiceAccepts } =>
        isRecord(part) &&
        typeof part.role === 'string' &&
        part.role.length > 0 &&
        isRecord(part.accepts),
    )
    .map((part) => ({ role: part.role, accepts: part.accepts as ChoiceAccepts }))
})
const composePartRoles = computed(() => composeParts.value.map((part) => part.role))

const targetZone = computed<GroupStoryFragment | undefined>(() => {
  const ref = targetZoneRef.value
  if (!ref) {
    return undefined
  }
  const fragment = props.fragments[ref]
  return fragment && isGroupFragment(fragment) ? fragment : undefined
})

const sourceZone = computed<GroupStoryFragment | undefined>(() => {
  const ref = sourceZoneRef.value
  if (!ref) {
    return undefined
  }
  const fragment = props.fragments[ref]
  return fragment && isGroupFragment(fragment) ? fragment : undefined
})

const piecesByPieceId = computed(() => {
  const pieces = new Map<string, PieceStoryFragment>()
  for (const fragment of Object.values(props.fragments)) {
    if (isPieceFragment(fragment) && fragment.piece_id) {
      pieces.set(fragment.piece_id, fragment)
    }
  }
  return pieces
})

const pieceByMemberId = (memberId: string): PieceStoryFragment | undefined => {
  const fragment = props.fragments[memberId]
  if (fragment && isPieceFragment(fragment)) {
    return fragment
  }
  return piecesByPieceId.value.get(memberId)
}

const isSelectablePiece = (piece: PieceStoryFragment): boolean => piece.available !== false

const candidatePieces = computed<PieceStoryFragment[]>(() =>
  targetZone.value?.member_ids
    .map(pieceByMemberId)
    .filter(
      (fragment): fragment is PieceStoryFragment =>
        fragment !== undefined && isSelectablePiece(fragment),
    ) ?? [],
)

const sourcePieces = computed<PieceStoryFragment[]>(() =>
  sourceZone.value?.member_ids
    .map(pieceByMemberId)
    .filter(
      (fragment): fragment is PieceStoryFragment =>
        fragment !== undefined && isSelectablePiece(fragment),
    ) ?? [],
)

const pieceLabel = (piece: PieceStoryFragment): string => {
  const hints = piece.hints ?? piece.presentation_hints
  const content = fragmentText(piece.content)
  return (
    stringValue(hints?.label_text) ??
    stringValue(piece.label) ??
    (content ? content : undefined) ??
    stringValue(piece.piece_id) ??
    piece.uid
  )
}

const zoneLabel = (zone: GroupStoryFragment | undefined, fallback: string): string => {
  if (!zone) {
    return fallback
  }
  const hints = zone.hints ?? zone.presentation_hints
  return (
    stringValue(hints?.label_text) ??
    stringValue(zone.label) ??
    stringValue(zone.zone_role) ??
    zone.uid
  )
}

const piecePayloadId = (piece: PieceStoryFragment): string => piece.piece_id ?? piece.uid
const candidatePiecePayloadIds = computed(() => candidatePieces.value.map(piecePayloadId))
const sourcePiecePayloadIds = computed(() => sourcePieces.value.map(piecePayloadId))
const sameStringList = (left: string[], right: string[]): boolean =>
  left.length === right.length && left.every((value, index) => value === right[index])

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

const piecePayload = (): PayloadState => {
  const min = minValue.value ?? (required.value ? 1 : 0)
  const max = maxValue.value ?? 1
  if (candidatePieces.value.length === 0 && min > 0) {
    return { valid: false, message: 'No valid targets' }
  }
  if (selectedPieceIds.value.length < min) {
    return { valid: false, message: min === max ? `Select ${min}` : `Select ${min}-${max}` }
  }
  if (selectedPieceIds.value.length > max) {
    return { valid: false, message: `Select at most ${max}` }
  }
  if (selectedPieceIds.value.length === 0) {
    return { valid: true, payload: props.choice.payload }
  }
  const validIds = new Set(candidatePiecePayloadIds.value)
  if (selectedPieceIds.value.some((pieceId) => !validIds.has(pieceId))) {
    return { valid: false, message: 'Select a valid target' }
  }
  return { valid: true, payload: { piece_ids: [...selectedPieceIds.value] } }
}

const placePayload = (): PayloadState => {
  const sourceRef = sourceZoneRef.value
  const targetRef = targetZoneRef.value
  if (!required.value && selectedPieceIds.value.length === 0) {
    return { valid: true, payload: props.choice.payload }
  }
  if (!sourceRef || !targetRef || !sourceZone.value || !targetZone.value) {
    return { valid: false, message: 'Missing source or target' }
  }
  if (sourcePieces.value.length === 0) {
    return { valid: false, message: 'No valid sources' }
  }
  if (selectedPieceIds.value.length !== 1) {
    return { valid: false, message: 'Select 1' }
  }
  const validIds = new Set(sourcePiecePayloadIds.value)
  const selectedPieceId = selectedPieceIds.value[0]
  if (!selectedPieceId || !validIds.has(selectedPieceId)) {
    return { valid: false, message: 'Select a valid source' }
  }
  return {
    valid: true,
    payload: {
      piece_id: selectedPieceId,
      source_zone_ref: sourceRef,
      target_zone_ref: targetRef,
    },
  }
}

const composePayload = (): PayloadState => {
  const parts = composeParts.value
  if (parts.length === 0) {
    return { valid: false, message: 'Missing parts' }
  }

  const payloadParts: Record<string, unknown> = {}
  for (const part of parts) {
    const state = composePartStates.value[part.role]
    if (!state?.valid) {
      return { valid: false, message: state?.message ?? 'Complete all parts' }
    }
    payloadParts[part.role] = state.payload ?? {}
  }
  return { valid: true, payload: { parts: payloadParts } }
}

const payloadState = computed<PayloadState>(() => {
  if (acceptsKind.value === 'text' || acceptsKind.value === 'raw_command') {
    return textPayload()
  }
  if (acceptsKind.value === 'quantity') {
    return quantityPayload()
  }
  if (acceptsKind.value === 'pieces') {
    return piecePayload()
  }
  if (acceptsKind.value === 'place') {
    return placePayload()
  }
  if (acceptsKind.value === 'compose') {
    return composePayload()
  }
  return { valid: true, payload: props.choice.payload }
})

const composePartLabel = (role: string): string => role.replace(/_/g, ' ')
const composePartChoice = (part: ComposePartInput): ChoiceStoryFragment => ({
  uid: `${props.choice.uid}:${part.role}`,
  fragment_type: 'choice',
  text: composePartLabel(part.role),
  accepts: part.accepts,
})

const handleComposePartPayload = (role: string, payload: unknown, valid: boolean) => {
  composePartStates.value = {
    ...composePartStates.value,
    [role]: { payload, valid },
  }
}

const togglePiece = (piece: PieceStoryFragment) => {
  if (props.disabled) {
    return
  }
  const id = piecePayloadId(piece)
  if (selectedPieceIds.value.includes(id)) {
    selectedPieceIds.value = selectedPieceIds.value.filter((selected) => selected !== id)
    return
  }

  const max = maxValue.value ?? 1
  if (max <= 1) {
    selectedPieceIds.value = [id]
    return
  }
  if (selectedPieceIds.value.length >= max) {
    return
  }
  selectedPieceIds.value = [...selectedPieceIds.value, id]
}

const handlePieceKeydown = (event: KeyboardEvent, piece: PieceStoryFragment) => {
  if (props.disabled) {
    return
  }
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    togglePiece(piece)
  }
}

watch(
  payloadState,
  (state) => emit('payloadChange', state.payload, state.valid),
  { immediate: true },
)

watch(
  [acceptsKind, sourceZoneRef, targetZoneRef],
  () => {
    inputValue.value = ''
    selectedPieceIds.value = []
    composePartStates.value = {}
  },
)

watch(
  composePartRoles,
  (roles) => {
    const roleSet = new Set(roles)
    const nextStates = Object.fromEntries(
      Object.entries(composePartStates.value).filter(([role]) => roleSet.has(role)),
    )
    if (Object.keys(nextStates).length !== Object.keys(composePartStates.value).length) {
      composePartStates.value = nextStates
    }
  },
)

watch(
  [candidatePiecePayloadIds, sourcePiecePayloadIds],
  ([candidateIds, sourceIds]) => {
    const validIds = new Set([...candidateIds, ...sourceIds])
    const nextSelected = selectedPieceIds.value.filter((pieceId) => validIds.has(pieceId))
    if (!sameStringList(selectedPieceIds.value, nextSelected)) {
      selectedPieceIds.value = nextSelected
    }
  },
)
</script>

<template>
  <div v-if="rendersInput" class="choice-input-view" data-testid="choice-input-view">
    <v-text-field
      v-if="acceptsKind === 'text' || acceptsKind === 'raw_command'"
      v-model="inputValue"
      class="choice-input"
      :class="{ 'choice-input--command': acceptsKind === 'raw_command' }"
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

    <div v-else-if="acceptsKind === 'pieces'" class="choice-piece-input">
      <div
        v-if="candidatePieces.length > 0"
        class="choice-piece-list"
        role="listbox"
        :aria-multiselectable="maxValue !== undefined && maxValue > 1 ? 'true' : undefined"
        :aria-label="inputLabel"
      >
        <div
          v-for="piece in candidatePieces"
          :key="piece.uid"
          class="choice-piece-option"
          :class="{ 'choice-piece-option--selected': selectedPieceIds.includes(piecePayloadId(piece)) }"
          role="option"
          :aria-selected="selectedPieceIds.includes(piecePayloadId(piece))"
          :aria-disabled="disabled ? 'true' : undefined"
          :data-piece-id="piecePayloadId(piece)"
          :tabindex="disabled ? undefined : 0"
          @click="togglePiece(piece)"
          @keydown="handlePieceKeydown($event, piece)"
        >
          {{ pieceLabel(piece) }}
        </div>
      </div>
    </div>

    <div v-else-if="acceptsKind === 'place'" class="choice-place-input">
      <div class="choice-place-target" data-testid="choice-place-target">
        {{ zoneLabel(sourceZone, 'source') }} to {{ zoneLabel(targetZone, 'target') }}
      </div>
      <div
        v-if="sourcePieces.length > 0"
        class="choice-piece-list"
        role="listbox"
        :aria-label="inputLabel"
      >
        <div
          v-for="piece in sourcePieces"
          :key="piece.uid"
          class="choice-piece-option"
          :class="{ 'choice-piece-option--selected': selectedPieceIds.includes(piecePayloadId(piece)) }"
          role="option"
          :aria-selected="selectedPieceIds.includes(piecePayloadId(piece))"
          :aria-disabled="disabled ? 'true' : undefined"
          :data-piece-id="piecePayloadId(piece)"
          :tabindex="disabled ? undefined : 0"
          @click="togglePiece(piece)"
          @keydown="handlePieceKeydown($event, piece)"
        >
          {{ pieceLabel(piece) }}
        </div>
      </div>
    </div>

    <div v-else-if="acceptsKind === 'compose'" class="choice-compose-input">
      <div
        v-for="part in composeParts"
        :key="part.role"
        class="choice-compose-part"
      >
        <div class="choice-compose-part-label">
          {{ composePartLabel(part.role) }}
        </div>
        <ChoiceInputView
          :choice="composePartChoice(part)"
          :fragments="fragments"
          :metadata="metadata"
          :disabled="disabled"
          @payload-change="(payload, valid) => handleComposePartPayload(part.role, payload, valid)"
          @commit="emit('commit')"
        />
      </div>
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

.choice-input--command {
  max-width: min(100%, 520px);
}

.choice-input--quantity {
  max-width: 180px;
}

.choice-input-unit {
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 0.78rem;
}

.choice-piece-input {
  min-width: 0;
}

.choice-place-input {
  display: grid;
  gap: 8px;
  min-width: 0;
}

.choice-compose-input {
  display: grid;
  gap: 10px;
}

.choice-compose-part {
  display: grid;
  gap: 4px;
}

.choice-compose-part-label {
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
}

.choice-place-target {
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 0.78rem;
  overflow-wrap: anywhere;
  padding: 0 4px;
}

.choice-piece-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.choice-piece-option {
  background: rgba(var(--v-theme-surface), 0.86);
  border: 1px solid rgba(var(--v-theme-primary), 0.34);
  border-radius: 6px;
  color: rgb(var(--v-theme-on-surface));
  cursor: pointer;
  font: inherit;
  min-height: 34px;
  padding: 6px 9px;
}

.choice-piece-option[aria-disabled='true'] {
  cursor: default;
  opacity: 0.6;
}

.choice-piece-option--selected {
  background: rgba(var(--v-theme-primary), 0.16);
  border-color: rgb(var(--v-theme-primary));
}

.choice-input-message {
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 0.78rem;
  padding: 0 4px;
}
</style>
