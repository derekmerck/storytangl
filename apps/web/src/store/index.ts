import { defineStore } from 'pinia'

import type { WorldInfo } from '@/types'
import { useGlobal } from '@/composables/globals'

interface StoreState {
  current_world_uid: string
  current_world_info?: WorldInfo
  user_secret: string
  user_api_key?: string
}

interface ApiKeyResponse {
  secret: string
  api_key: string
}

const { $http, makeMediaDict } = useGlobal()

export const useStore = defineStore('main', {
  state: (): StoreState => ({
    current_world_uid: import.meta.env.VITE_DEFAULT_WORLD,
    current_world_info: undefined,
    user_secret: import.meta.env.VITE_DEFAULT_USER_SECRET,
    user_api_key: undefined,
  }),

  actions: {
    async setCurrentWorld(worldUid: string) {
      this.current_world_uid = worldUid

      try {
        await $http.value.put('/user/world', { uid: worldUid })
      } catch (error) {
        console.error('Failed to set current world.', error)
      }

      await this.getCurrentWorldInfo()
    },

    async getCurrentWorldInfo() {
      const response = await $http.value.get<WorldInfo>(`/world/${this.current_world_uid}/info`)
      const world = response.data

      if (world?.media) {
        world.media_dict = makeMediaDict(world)
      }

      this.current_world_info = world
    },

    async getApiKey() {
      const response = await $http.value.get<ApiKeyResponse>('/system/secret', {
        params: { secret: this.user_secret },
      })

      this.user_secret = response.data.secret
      this.user_api_key = response.data.api_key
      $http.value.defaults.headers.common['X-Api-Key'] = response.data.api_key
    },

    async setApiKey(secret: string) {
      const response = await $http.value.put<ApiKeyResponse>('/user/secret', { secret })

      this.user_secret = response.data.secret
      this.user_api_key = response.data.api_key
      $http.value.defaults.headers.common['X-Api-Key'] = response.data.api_key
    },
  },
})
