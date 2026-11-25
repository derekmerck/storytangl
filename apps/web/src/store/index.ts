import { defineStore } from 'pinia'

import type {
  BrandingValue,
  PreferenceDeclaration,
  PreferenceValue,
  ProjectedState,
  UserInfo,
  UserSecretResponse,
} from '@/types'
import { useGlobal } from '@/composables/globals'
import { savePlayerSecret } from '@/playerSession'
import { loadPreferenceValues, savePreferenceValues, type PreferenceValues } from '@/worldPreferences'

interface StoreState {
  current_world_uid: string
  current_world_info?: BrandingValue
  /** The current world's declared viewer preferences, and this browser's values for them. */
  world_preferences: PreferenceDeclaration[]
  preference_values: PreferenceValues
  current_user?: UserInfo
  user_secret: string
  user_api_key?: string
}

const { $http } = useGlobal()

export const useStore = defineStore('main', {
  state: (): StoreState => ({
    current_world_uid: import.meta.env.VITE_DEFAULT_WORLD,
    current_world_info: undefined,
    world_preferences: [],
    preference_values: {},
    user_secret: import.meta.env.VITE_DEFAULT_USER_SECRET,
    user_api_key: undefined,
  }),

  actions: {
    async setCurrentWorld(worldUid: string) {
      this.current_world_uid = worldUid
      await this.getCurrentWorldInfo()
    },

    async getCurrentWorldInfo() {
      const worldUid = this.current_world_uid
      const response = await $http.value.get<ProjectedState>(`/world/${worldUid}/info`, {
        params: { channels: 'ui-branding' },
      })
      if (this.current_world_uid !== worldUid) return
      const value = response.data.sections.find(
        (section) => section.value.value_type === 'branding'
      )?.value
      this.current_world_info = value?.value_type === 'branding' ? value : undefined
    },

    /**
     * Fetch the world-static presentation channels this world advertises. A
     * world that declares no preferences advertises no `ui-preferences`
     * channel, and is not asked for one.
     */
    async getWorldPresentation(worldUid: string) {
      const catalog = await $http.value.get<ProjectedState>(`/world/${worldUid}/info`)
      const advertised = catalog.data.channels.some(
        (channel) => channel.channel_id === 'ui-preferences'
      )
      if (this.current_world_uid !== worldUid || !advertised) return
      const response = await $http.value.get<ProjectedState>(`/world/${worldUid}/info`, {
        params: { channels: 'ui-preferences' },
      })
      if (this.current_world_uid !== worldUid) return
      for (const { value } of response.data.sections) {
        if (value.value_type === 'ui_preferences') {
          this.world_preferences = value.preferences
          this.preference_values = loadPreferenceValues(worldUid, value.preferences)
        }
      }
    },

    setPreference(id: string, value: PreferenceValue) {
      this.preference_values = { ...this.preference_values, [id]: value }
      savePreferenceValues(this.current_world_uid, this.preference_values)
    },

    async authenticateWithSecret(secret: string) {
      delete $http.value.defaults.headers.common['X-Api-Key']
      const response = await $http.value.get<UserSecretResponse>('/system/secret', {
        params: { secret },
      })
      $http.value.defaults.headers.common['X-Api-Key'] = response.data.api_key

      try {
        const user = await $http.value.get<UserInfo>('/user/info')
        this.current_user = user.data
      } catch (error) {
        delete $http.value.defaults.headers.common['X-Api-Key']
        throw error
      }

      this.user_secret = response.data.user_secret
      this.user_api_key = response.data.api_key
      savePlayerSecret(this.user_secret)
    },

    async ensurePlayer(secret?: string) {
      const response = await $http.value.post<UserSecretResponse>('/user/create', undefined, {
        params: secret ? { secret } : undefined,
      })
      $http.value.defaults.headers.common['X-Api-Key'] = response.data.api_key
      try {
        const user = await $http.value.get<UserInfo>('/user/info')

        this.current_user = user.data
      } catch (error) {
        delete $http.value.defaults.headers.common['X-Api-Key']
        throw error
      }

      this.user_secret = response.data.user_secret
      this.user_api_key = response.data.api_key
      savePlayerSecret(this.user_secret)
    },

    async rotateSecret(secret: string) {
      const response = await $http.value.put<UserSecretResponse>('/user/secret', undefined, {
        params: { secret },
      })

      this.user_secret = response.data.user_secret
      this.user_api_key = response.data.api_key
      $http.value.defaults.headers.common['X-Api-Key'] = response.data.api_key
      savePlayerSecret(this.user_secret)
    },
  },
})
