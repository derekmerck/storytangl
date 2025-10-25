import axios from 'axios'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const DEFAULT_API_URL = 'http://localhost:8000/api/v2'

let useStore: typeof import('./index')['useStore']
let useGlobal: typeof import('@/composables/globals')['useGlobal']

beforeEach(async () => {
  vi.unstubAllEnvs()
  vi.stubEnv('VITE_DEFAULT_API_URL', DEFAULT_API_URL)
  vi.stubEnv('VITE_DEFAULT_WORLD', 'tangl_world')
  vi.stubEnv('VITE_DEFAULT_USER_SECRET', 'dev-secret-123')

  setActivePinia(createPinia())

  vi.resetModules()
  ;({ useStore } = await import('./index'))
  ;({ useGlobal } = await import('@/composables/globals'))
})

afterEach(() => {
  vi.unstubAllEnvs()
  delete axios.defaults.headers.common?.['X-Api-Key']
})

describe('Store', () => {
  it('initializes with default world from env', () => {
    const store = useStore()
    expect(store.current_world_uid).toBe('tangl_world')
  })

  it('initializes with user secret from env', () => {
    const store = useStore()
    expect(store.user_secret).toBe('dev-secret-123')
  })

  it('fetches world info and transforms media', async () => {
    const store = useStore()
    await store.getCurrentWorldInfo()

    expect(store.current_world_info).toBeDefined()
    expect(store.current_world_info?.media_dict?.cover_im?.url).toBeDefined()
  })

  it('changes world and fetches new info', async () => {
    const store = useStore()
    await store.setCurrentWorld('new_world')

    expect(store.current_world_uid).toBe('new_world')
    expect(store.current_world_info?.world_id).toBe('new_world')
  })

  it('gets API key from user secret', async () => {
    const store = useStore()
    await store.getApiKey()

    const { $http } = useGlobal()
    expect(store.user_api_key).toBeDefined()
    expect($http.value.defaults.headers.common['X-Api-Key']).toBe(store.user_api_key)
  })

  it('sets new API key when secret changes', async () => {
    const store = useStore()
    await store.setApiKey('new-secret-123')

    const { $http } = useGlobal()
    expect(store.user_secret).toBe('new-secret-123')
    expect(store.user_api_key).toBeDefined()
    expect($http.value.defaults.headers.common['X-Api-Key']).toBe(store.user_api_key)
  })
})
