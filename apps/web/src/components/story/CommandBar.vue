<script setup lang="ts">
import { computed, ref } from 'vue'

import type { UxEvent } from '@/types'

type CommandGrammar = {
  examples?: unknown
  placeholder?: unknown
}

const props = defineProps<{
  grammar: CommandGrammar
  events?: UxEvent[]
  disabled?: boolean
}>()

const emit = defineEmits<{
  submit: [command: string]
}>()

const command = ref('')
const examples = computed(() =>
  Array.isArray(props.grammar.examples)
    ? props.grammar.examples.filter(
        (example): example is string => typeof example === 'string' && example.length > 0,
      )
    : [],
)
const placeholder = computed(() => {
  if (typeof props.grammar.placeholder === 'string' && props.grammar.placeholder) {
    return props.grammar.placeholder
  }
  return examples.value.length > 0 ? `e.g. ${examples.value[0]}` : 'Type a command'
})

const submit = () => {
  const value = command.value.trim()
  if (!value || props.disabled) {
    return
  }
  emit('submit', value)
}
</script>

<template>
  <div
    class="command-bar"
    data-testid="command-bar"
  >
    <v-form
      class="command-form"
      @submit.prevent="submit"
    >
      <v-text-field
        v-model="command"
        aria-label="Story command"
        density="comfortable"
        hide-details
        :disabled="disabled"
        :placeholder="placeholder"
        prepend-inner-icon="mdi-chevron-right"
        variant="outlined"
      />
      <v-tooltip text="Submit command">
        <template #activator="{ props: tooltipProps }">
          <v-btn
            v-bind="tooltipProps"
            aria-label="Submit command"
            color="primary"
            :disabled="disabled || !command.trim()"
            icon="mdi-send"
            type="submit"
            variant="tonal"
          />
        </template>
      </v-tooltip>
    </v-form>

    <v-alert
      v-for="event in events ?? []"
      :key="event.event_id"
      class="mt-2"
      :type="event.severity"
      density="compact"
      data-testid="inline-ux-event"
      variant="tonal"
    >
      {{ event.message }}
    </v-alert>
  </div>
</template>

<style scoped>
.command-bar {
  margin-top: 12px;
}

.command-form {
  align-items: center;
  display: grid;
  gap: 8px;
  grid-template-columns: minmax(0, 1fr) 44px;
}
</style>
