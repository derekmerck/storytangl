<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'

import WorldInfo from '@/components/dialogs/WorldInfo.vue'
import SystemInfo from '@/components/dialogs/SystemInfo.vue'
import SecretDialog from '@/components/dialogs/SecretDialog.vue'
import { useGlobal } from '@/composables/globals'
import type { WorldList } from '@/types'
import { useStore } from '@/store'

const emit = defineEmits<{
  'toggle-drawer': []
  'recover-player': []
  'select-world': [worldId: string]
}>()
defineProps<{ busy?: boolean }>()

const { $http, remapURL } = useGlobal()
const store = useStore()

const worlds = ref<WorldList>([])
const catalogError = ref('')
const showWorldInfo = ref(false)
const showSystemInfo = ref(false)
const showSecretDialog = ref(false)

const guideUrl = computed((): string => '/guide')

onMounted(async () => {
  try {
    if (store.current_world_uid && !store.current_world_info) {
      await store.getCurrentWorldInfo()
    }
  } catch (error) {
    console.error('Failed to fetch current world info.', error)
  }

  try {
    const response = await $http.value.get<WorldList>('/system/worlds')
    worlds.value = response.data ?? []
  } catch (error) {
    console.error('Failed to fetch worlds:', error)
    catalogError.value = 'Unable to load worlds. Reload to retry.'
  }
})

const selectWorld = (worldId: string) => emit('select-world', worldId)

const openGuide = () => {
  const target = guideUrl.value
  if (!target) {
    return
  }

  const resolved = remapURL(target)
  window.open(resolved, 'StoryTangl User Guide')
}
</script>

<template>
  <div>
    <v-app-bar color="primary">
      <v-app-bar-nav-icon aria-label="menu" @click="emit('toggle-drawer')" />
      <v-app-bar-title class="title">WebTangl</v-app-bar-title>
      <v-spacer />

      <v-menu>
        <template #activator="{ props }">
          <v-btn v-bind="props" :disabled="busy" variant="text" color="on-primary"> Worlds </v-btn>
        </template>
        <v-list density="compact">
          <v-list-item v-if="catalogError || !worlds.length">
            {{ catalogError || 'No worlds available.' }}
          </v-list-item>
          <v-list-item
            v-for="world in worlds"
            :key="world.label"
            :disabled="busy"
            @click="selectWorld(world.label)"
          >
            <v-list-item-title>
              {{ world.title || world.label }}
            </v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>

      <v-menu>
        <template #activator="{ props }">
          <v-btn v-bind="props" variant="text" color="on-primary"> User </v-btn>
        </template>
        <v-list density="compact">
          <v-list-item v-if="store.current_user">
            <v-list-item-title>{{ store.current_user.user_id }}</v-list-item-title>
          </v-list-item>
          <v-list-item @click="showSecretDialog = true">
            <v-list-item-title>Change Secret</v-list-item-title>
          </v-list-item>
          <v-list-item @click="emit('recover-player')">
            <v-list-item-title>Switch or Recover Player</v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>

      <v-menu>
        <template #activator="{ props }">
          <v-btn v-bind="props" variant="text" color="on-primary"> Info </v-btn>
        </template>
        <v-list density="compact">
          <v-list-item @click="showWorldInfo = true">
            <v-list-item-title>World Info</v-list-item-title>
          </v-list-item>
          <v-list-item @click="showSystemInfo = true">
            <v-list-item-title>System Info</v-list-item-title>
          </v-list-item>
          <v-list-item v-if="guideUrl" @click="openGuide">
            <v-list-item-title>User Guide</v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>
    </v-app-bar>

    <WorldInfo v-model="showWorldInfo" />
    <SystemInfo v-model="showSystemInfo" />
    <SecretDialog v-model="showSecretDialog" />
  </div>
</template>
