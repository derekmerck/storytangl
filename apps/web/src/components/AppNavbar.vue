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
}>()

const { $http, remapURL } = useGlobal()
const store = useStore()

const worlds = ref<WorldList>([])
const showWorldInfo = ref(false)
const showSystemInfo = ref(false)
const showSecretDialog = ref(false)

const guideUrl = computed((): string => store.current_world_info?.guide_url ?? '/guide')

onMounted(async () => {
  try {
    if (!store.current_world_info) {
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
  }
})

const selectWorld = async (worldId: string) => {
  try {
    await $http.value.put('/user/world', { uid: worldId })
    await store.setCurrentWorld(worldId)
  } catch (error) {
    console.error('Failed to select world:', error)
  }
}

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
          <v-btn v-bind="props" variant="text" color="on-primary">
            Worlds
          </v-btn>
        </template>
        <v-list density="compact">
          <v-list-item
            v-for="world in worlds"
            :key="world.key"
            @click="selectWorld(world.key)"
          >
            <v-list-item-title :style="(world.style ?? world.style_dict) as Record<string, string | number>">
              {{ world.value }}
            </v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>

      <v-menu>
        <template #activator="{ props }">
          <v-btn v-bind="props" variant="text" color="on-primary">
            User
          </v-btn>
        </template>
        <v-list density="compact">
          <v-list-item @click="showSecretDialog = true">
            <v-list-item-title>Set Secret</v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>

      <v-menu>
        <template #activator="{ props }">
          <v-btn v-bind="props" variant="text" color="on-primary">
            Info
          </v-btn>
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
