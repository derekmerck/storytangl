<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useDisplay } from 'vuetify'

import AppNavbar from '@/components/AppNavbar.vue'
import AppFooter from '@/components/AppFooter.vue'
import StoryStatus from '@/components/StoryStatus.vue'
import StoryFlow from '@/components/story/StoryFlow.vue'
import type { InfoAffordance, InfoState, RuntimeEnvelope } from '@/types'
import { clearPlayerSecret, loadPlayerSecret } from '@/playerSession'
import { useStore } from '@/store'

const drawer = ref(true)
const statusRefreshKey = ref(0)
const infoAffordances = ref<InfoAffordance[]>([])
const infoState = ref<InfoState | null>(null)
const clientState = ref<'initializing' | 'needs-auth' | 'ready'>('initializing')
const authenticationError = ref<string | null>(null)
const authenticationSecret = ref('')
const store = useStore()
const display = useDisplay()

const isDesktop = computed(() => display.mdAndUp.value)

const bootstrapPlayer = async (action: () => Promise<void>) => {
  clientState.value = 'initializing'
  authenticationError.value = null
  try {
    await action()
    clientState.value = 'ready'
  } catch (error) {
    console.error('Failed to initialize authentication:', error)
    authenticationError.value = 'Unable to authenticate with the story service.'
    clientState.value = 'needs-auth'
  }
}

const useExistingSecret = async () => {
  if (!authenticationSecret.value) {
    authenticationError.value = 'Enter a recovery secret.'
    return
  }
  await bootstrapPlayer(() => store.ensurePlayer(authenticationSecret.value))
}

const startNewPlayer = async () => {
  await bootstrapPlayer(() => store.ensurePlayer())
}

const restoreStoredPlayer = async () => {
  await bootstrapPlayer(() => store.authenticateWithSecret(authenticationSecret.value))
}

const initializeClient = async () => {
  const storedSecret = loadPlayerSecret()
  authenticationSecret.value = storedSecret ?? store.user_secret
  if (!authenticationSecret.value) {
    await startNewPlayer()
    return
  }
  await restoreStoredPlayer()
  if (clientState.value !== 'ready' && storedSecret) {
    clearPlayerSecret()
  }
}

const recoverPlayer = () => {
  authenticationSecret.value = ''
  authenticationError.value = null
  clientState.value = 'needs-auth'
}

onMounted(() => {
  drawer.value = isDesktop.value
  void initializeClient()
})

const toggleDrawer = () => {
  drawer.value = !drawer.value
}

const refreshStatus = () => {
  statusRefreshKey.value += 1
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

const normalizeInfoAffordances = (value: unknown): InfoAffordance[] => {
  if (!Array.isArray(value)) {
    return []
  }
  return value
    .filter(isRecord)
    .map((item) => {
      const kind = typeof item.kind === 'string' ? item.kind : ''
      const shortcuts = Array.isArray(item.shortcuts)
        ? item.shortcuts.filter((shortcut): shortcut is string => typeof shortcut === 'string')
        : []
      return {
        kind,
        label: typeof item.label === 'string' ? item.label : undefined,
        shortcuts,
        query: isRecord(item.query) ? item.query : undefined,
      }
    })
    .filter((item) => item.kind.length > 0)
}

const normalizeInfoState = (value: unknown): InfoState | null => {
  if (!isRecord(value)) {
    return null
  }
  const dirtyKinds = Array.isArray(value.dirty_kinds)
    ? value.dirty_kinds.filter((kind): kind is string => typeof kind === 'string')
    : undefined
  const availableKinds = Array.isArray(value.available_kinds)
    ? value.available_kinds.filter((kind): kind is string => typeof kind === 'string')
    : undefined
  return {
    version: typeof value.version === 'number' ? value.version : undefined,
    dirty_kinds: dirtyKinds,
    available_kinds: availableKinds,
  }
}

const handleStoryUpdate = (envelope: RuntimeEnvelope) => {
  if (
    envelope.metadata &&
    Object.prototype.hasOwnProperty.call(envelope.metadata, 'info_affordances')
  ) {
    infoAffordances.value = normalizeInfoAffordances(envelope.metadata.info_affordances)
  }
  if (envelope.metadata && Object.prototype.hasOwnProperty.call(envelope.metadata, 'info_state')) {
    infoState.value = normalizeInfoState(envelope.metadata.info_state)
  }
  refreshStatus()
}
</script>

<template>
  <v-app id="webtangl">
    <v-main v-if="clientState === 'needs-auth'">
      <v-container class="py-6" fluid>
        <v-card class="mx-auto" max-width="480">
          <v-card-title>Recover Player</v-card-title>
          <v-card-text>
            <p class="mb-4">Use a recovery secret from another browser, or start a new player.</p>
            <v-text-field
              v-model="authenticationSecret"
              data-testid="authentication-secret"
              label="Recovery Secret"
              type="password"
            />
            <v-alert
              v-if="authenticationError"
              data-testid="authentication-error"
              density="compact"
              type="error"
              variant="tonal"
            >
              {{ authenticationError }}
            </v-alert>
          </v-card-text>
          <v-card-actions>
            <v-btn
              data-testid="authentication-existing"
              variant="text"
              @click="useExistingSecret"
            >
              Use Recovery Secret
            </v-btn>
            <v-spacer />
            <v-btn data-testid="authentication-create" color="primary" @click="startNewPlayer">
              Start New Player
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-container>
    </v-main>

    <template v-else-if="clientState === 'ready'">
      <AppNavbar @toggle-drawer="toggleDrawer" @recover-player="recoverPlayer" />

      <v-navigation-drawer
        v-model="drawer"
        :permanent="isDesktop"
        width="260"
        border="0"
      >
        <v-list density="compact">
          <v-list-item>
            <v-list-item-title class="text-h6">Status</v-list-item-title>
          </v-list-item>
        </v-list>
        <v-divider class="mb-2" />
        <StoryStatus
          :refresh-key="statusRefreshKey"
          :info-affordances="infoAffordances"
          :info-state="infoState"
        />
      </v-navigation-drawer>

      <v-main>
        <v-container class="py-6" fluid>
          <v-row justify="center">
            <v-col cols="12" lg="9">
              <StoryFlow @story-update="handleStoryUpdate" />
            </v-col>
          </v-row>
          <AppFooter />
        </v-container>
      </v-main>
    </template>

    <v-progress-linear v-else color="primary" indeterminate />
  </v-app>
</template>
