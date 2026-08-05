<script setup lang="ts">
import { ref, watch } from 'vue'

import { useStore } from '@/store'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const store = useStore()
const secret = ref(store.user_secret)
const loading = ref(false)

watch(
  () => props.modelValue,
  (isOpen) => {
    if (isOpen) {
      secret.value = store.user_secret
    }
  },
)

const close = () => {
  emit('update:modelValue', false)
}

const copySecret = async () => {
  await navigator.clipboard.writeText(secret.value)
}

const save = async () => {
  if (!secret.value) {
    close()
    return
  }

  loading.value = true
  try {
    await store.rotateSecret(secret.value)
    close()
  } catch (error) {
    console.error('Failed to set API key:', error)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <v-dialog :model-value="modelValue" max-width="480" persistent>
    <v-card>
      <v-card-title>Recovery Secret</v-card-title>
      <v-card-text>
        <v-text-field
          v-model="secret"
          label="Recovery Secret"
          hint="Keep this secret to recover the current player on another browser"
          persistent-hint
          :disabled="loading"
          autofocus
        />
      </v-card-text>
      <v-card-actions>
        <v-btn variant="text" @click="copySecret" :disabled="loading">
          Copy
        </v-btn>
        <v-spacer />
        <v-btn variant="text" @click="close" :disabled="loading">
          Cancel
        </v-btn>
        <v-btn color="primary" @click="save" :loading="loading">
          Save
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
