<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { useStore } from '@/store'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const store = useStore()
const loading = ref(false)
const error = ref<string | null>(null)

const worldInfo = computed(() => store.current_world_info)
const coverImage = computed(() => worldInfo.value?.media_dict?.cover_im?.url)

const ensureWorldInfo = async () => {
  if (worldInfo.value || loading.value) {
    return
  }

  try {
    loading.value = true
    error.value = null
    await store.getCurrentWorldInfo()
  } catch (err) {
    console.error('Failed to load world info:', err)
    error.value = 'Unable to load world information.'
  } finally {
    loading.value = false
  }
}

watch(
  () => props.modelValue,
  async (isOpen) => {
    if (isOpen) {
      await ensureWorldInfo()
    }
  },
  { immediate: true },
)

const close = () => {
  emit('update:modelValue', false)
}
</script>

<template>
  <v-dialog :model-value="modelValue" max-width="640">
    <v-card>
      <v-img v-if="coverImage" :src="coverImage" height="200" cover />

      <v-card-title>
        {{ worldInfo?.title ?? 'World Info' }}
      </v-card-title>

      <v-card-subtitle v-if="worldInfo?.version">
        Version {{ worldInfo.version }}
      </v-card-subtitle>

      <v-card-text>
        <div v-if="error" class="text-error">{{ error }}</div>
        <div v-else-if="loading">Loading world information...</div>
        <div v-else-if="worldInfo?.summary">{{ worldInfo.summary }}</div>
        <div v-else>World details are not available.</div>
      </v-card-text>

      <v-card-text v-if="worldInfo?.comments">
        {{ worldInfo.comments }}
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="close">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
