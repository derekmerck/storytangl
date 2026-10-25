<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useDisplay } from 'vuetify'

import AppNavbar from '@/components/AppNavbar.vue'
import AppFooter from '@/components/AppFooter.vue'
import StoryStatus from '@/components/StoryStatus.vue'
import StoryFlow from '@/components/story/StoryFlow.vue'
import type { InfoState, RuntimeEnvelope, UserInfo } from '@/types'
import { useGlobal } from '@/composables/globals'
import { clearPlayerSecret, loadPlayerSecret } from '@/playerSession'
import { useStore } from '@/store'
import { isChoiceFragment, normalizeEnvelope } from '@/components/story/fragmentUtils'

const drawer = ref(true)
const statusRefreshKey = ref(0)
const infoState = ref<InfoState | null>(null)
const clientState = ref<'initializing' | 'needs-auth' | 'ready'>('initializing')
const authenticationError = ref<string | null>(null)
const authenticationSecret = ref('')
const authenticationPending = ref(false)
const store = useStore()
const display = useDisplay()

const isDesktop = computed(() => display.mdAndUp.value)
const sessionGeneration = ref(0)
onBeforeUnmount(() => {
  sessionGeneration.value += 1
})
const sessionLoading = ref(false)
const writePending = ref(false)
const sessionError = ref<string | null>(null)
const sessionUncertain = ref(false)
const activeSession = ref<{ envelope: RuntimeEnvelope; choiceIds: string[] } | null>(null)
const { $http } = useGlobal()
const sessionBusy = computed(
  () => sessionLoading.value || writePending.value || sessionUncertain.value
)

const resetSession = () => {
  sessionGeneration.value += 1
  activeSession.value = null
  infoState.value = null
  statusRefreshKey.value = 0
  store.current_world_uid = ''
  store.current_world_info = undefined
}

const decodeEnvelope = (payload: unknown): RuntimeEnvelope => {
  const envelope = normalizeEnvelope(payload, { fallbackPrefix: 'session' })
  if (
    !envelope ||
    typeof envelope.metadata?.ledger_id !== 'string' ||
    typeof envelope.metadata?.world_id !== 'string'
  ) {
    throw new Error('Missing story identity in response')
  }
  return envelope
}

const activateSession = (envelope: RuntimeEnvelope, current: RuntimeEnvelope) => {
  if (
    envelope.metadata?.ledger_id !== current.metadata?.ledger_id ||
    envelope.step !== current.step
  ) {
    throw new Error('Story changed while loading; retry the current story')
  }
  store.current_world_uid = envelope.metadata!.world_id as string
  if (store.current_user)
    store.current_user.current_ledger_id = envelope.metadata!.ledger_id as string
  activeSession.value = {
    envelope,
    choiceIds: current.fragments.filter(isChoiceFragment).map((fragment) => fragment.uid),
  }
  sessionUncertain.value = false
}

const resumeStory = async () => {
  resetSession()
  const generation = sessionGeneration.value
  sessionLoading.value = true
  try {
    const history = decodeEnvelope((await $http.value.get('/story/update')).data)
    if (generation !== sessionGeneration.value) return
    const current = decodeEnvelope(
      (
        await $http.value.get('/story/update', {
          params: { since_step: history.step },
        })
      ).data
    )
    if (generation !== sessionGeneration.value) return
    activateSession(history, current)
  } catch {
    if (generation === sessionGeneration.value) {
      sessionError.value =
        'Unable to continue the current story. Retry without creating a replacement.'
      sessionUncertain.value = true
    }
  } finally {
    if (generation === sessionGeneration.value) sessionLoading.value = false
  }
}

const synchronizePlayer = async () => {
  if (sessionLoading.value || writePending.value) return
  sessionError.value = null
  sessionLoading.value = true
  const generation = sessionGeneration.value
  try {
    const user = await $http.value.get<UserInfo>('/user/info')
    if (generation !== sessionGeneration.value) return
    store.current_user = user.data
    if (user.data.current_ledger_id) {
      await resumeStory()
    } else {
      resetSession()
      sessionUncertain.value = false
    }
  } catch {
    sessionError.value = 'Unable to check the current story. Please retry.'
    sessionUncertain.value = true
  } finally {
    sessionLoading.value = false
  }
}

const startStory = async (worldId: string) => {
  if (sessionBusy.value) return
  resetSession()
  const generation = sessionGeneration.value
  sessionLoading.value = true
  sessionError.value = null
  try {
    const envelope = decodeEnvelope(
      (
        await $http.value.post('/story/create', undefined, {
          params: { world_id: worldId, init_mode: 'EAGER' },
        })
      ).data
    )
    if (generation === sessionGeneration.value) activateSession(envelope, envelope)
  } catch {
    if (generation === sessionGeneration.value) {
      sessionError.value = 'Story creation failed. Check the current story before trying again.'
      sessionUncertain.value = true
    }
  } finally {
    if (generation === sessionGeneration.value) sessionLoading.value = false
  }
}

const resynchronizeStory = async (message: string) => {
  writePending.value = false
  sessionError.value = `${message} Checking the current story before another move.`
  await resumeStory()
}

const bootstrapPlayer = async (action: () => Promise<void>) => {
  if (authenticationPending.value) return
  authenticationPending.value = true
  clientState.value = 'initializing'
  resetSession()
  const generation = sessionGeneration.value
  sessionError.value = null
  sessionUncertain.value = false
  authenticationError.value = null
  try {
    await action()
    if (generation !== sessionGeneration.value) return
    clientState.value = 'ready'
    if (store.current_user?.current_ledger_id) await resumeStory()
  } catch (error) {
    if (generation !== sessionGeneration.value) return
    console.error('Failed to initialize authentication:', error)
    authenticationError.value = 'Unable to authenticate with the story service.'
    clientState.value = 'needs-auth'
  } finally {
    authenticationPending.value = false
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
  if (sessionLoading.value || writePending.value) return
  resetSession()
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

const normalizeInfoState = (value: unknown): InfoState | null => {
  if (!isRecord(value)) {
    return null
  }
  const dirtyChannels = Array.isArray(value.dirty_channels)
    ? value.dirty_channels.filter((channel): channel is string => typeof channel === 'string')
    : undefined
  const availableChannels = Array.isArray(value.available_channels)
    ? value.available_channels.filter((channel): channel is string => typeof channel === 'string')
    : undefined
  return {
    version: typeof value.version === 'number' ? value.version : undefined,
    dirty_channels: dirtyChannels,
    available_channels: availableChannels,
  }
}

const handleStoryUpdate = (envelope: RuntimeEnvelope) => {
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
            <v-btn data-testid="authentication-existing" variant="text" @click="useExistingSecret">
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
      <AppNavbar
        :busy="sessionBusy"
        @select-world="startStory"
        @toggle-drawer="toggleDrawer"
        @recover-player="recoverPlayer"
      />

      <v-navigation-drawer
        v-if="activeSession"
        :key="sessionGeneration"
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
        <StoryStatus :refresh-key="statusRefreshKey" :info-state="infoState" />
      </v-navigation-drawer>

      <v-main>
        <v-container class="py-6" fluid>
          <v-row justify="center">
            <v-col cols="12" lg="9">
              <v-progress-linear v-if="sessionLoading" indeterminate />
              <v-alert v-if="sessionError" type="error">{{ sessionError }}</v-alert>
              <v-btn v-if="sessionUncertain" :disabled="sessionLoading" @click="synchronizePlayer">
                Retry current story
              </v-btn>
              <p v-if="!activeSession && !sessionLoading && !sessionError">
                Choose a world from Worlds to start a story.
              </p>
              <StoryFlow
                v-if="activeSession"
                :key="sessionGeneration"
                :initial-envelope="activeSession.envelope"
                :active-choice-ids="activeSession.choiceIds"
                @write-pending="writePending = $event"
                @resynchronize="resynchronizeStory"
                @story-update="handleStoryUpdate"
              />
            </v-col>
          </v-row>
          <AppFooter />
        </v-container>
      </v-main>
    </template>

    <v-progress-linear v-else color="primary" indeterminate />
  </v-app>
</template>
