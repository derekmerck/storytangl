<script setup lang="ts">
import { ref, watch } from 'vue'

import { useGlobal } from '@/composables/globals'

type SystemInfoPayload = Record<string, string | number | boolean | null>

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const { $http } = useGlobal()
const systemInfo = ref<SystemInfoPayload | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

const fetchSystemInfo = async () => {
  try {
    loading.value = true
    error.value = null
    const response = await $http.value.get<SystemInfoPayload>('/system/info')
    systemInfo.value = response.data
  } catch (err) {
    console.error('Failed to fetch system info:', err)
    error.value = 'Unable to load system information.'
    systemInfo.value = null
  } finally {
    loading.value = false
  }
}

watch(
  () => props.modelValue,
  async (isOpen) => {
    if (isOpen && !systemInfo.value) {
      await fetchSystemInfo()
    }
  },
  { immediate: true },
)

const close = () => {
  emit('update:modelValue', false)
}
</script>

<template>
  <v-dialog :model-value="modelValue" max-width="560">
    <v-card>
      <v-card-title>System Information</v-card-title>

      <v-card-text>
        <div v-if="error" class="text-error">{{ error }}</div>
        <div v-else-if="loading">Loading system information...</div>
        <v-list v-else-if="systemInfo" density="compact">
          <v-list-item v-for="(value, key) in systemInfo" :key="key">
            <v-list-item-title class="font-weight-medium text-body-2">{{ key }}</v-list-item-title>
            <v-list-item-subtitle>{{ value }}</v-list-item-subtitle>
          </v-list-item>
        </v-list>
        <div v-else>No system details available.</div>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="close">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
