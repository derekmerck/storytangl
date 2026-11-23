import axios from 'axios'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { http, HttpResponse, server } from '@tests/setup'
import { flushPromises } from '@vue/test-utils'
import { reparteePresentationInfo, reparteeWorldCatalog } from '@tests/fixtures'

const DEFAULT_API_URL = 'http://localhost:8000/api/v2'

let useStore: (typeof import('./index'))['useStore']
let useGlobal: (typeof import('@/composables/globals'))['useGlobal']

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
  it('ignores branding from a previously selected world', async () => {
    let release!: () => void
    server.use(
      http.get(
        `${DEFAULT_API_URL}/world/old/info`,
        () =>
          new Promise((resolve) => {
            release = () =>
              resolve(
                HttpResponse.json({
                  sections: [
                    {
                      section_id: 'ui-branding',
                      title: 'Branding',
                      value: { value_type: 'branding', name: 'Old world' },
                    },
                  ],
                })
              )
          })
      )
    )
    const store = useStore()
    store.current_world_uid = 'old'
    const previous = store.getCurrentWorldInfo()
    await flushPromises()
    await store.setCurrentWorld('new_world')
    release()
    await previous
    expect(store.current_world_info?.name).toBe('new_world')
  })
  it('initializes with default world from env', () => {
    const store = useStore()
    expect(store.current_world_uid).toBe('tangl_world')
  })

  it('initializes with user secret from env', () => {
    const store = useStore()
    expect(store.user_secret).toBe('dev-secret-123')
  })

  it('fetches the world branding projection', async () => {
    const store = useStore()
    await store.getCurrentWorldInfo()

    expect(store.current_world_info).toBeDefined()
    expect(store.current_world_info?.name).toBe('My world!')
    expect(store.current_world_info?.logo_media).toBe('cover_im')
  })

  it('changes world and fetches new info', async () => {
    const store = useStore()
    await store.setCurrentWorld('new_world')

    expect(store.current_world_uid).toBe('new_world')
    expect(store.current_world_info?.name).toBe('new_world')
  })

  it('authenticates a persisted user from a user secret', async () => {
    const store = useStore()
    await store.authenticateWithSecret(store.user_secret)

    const { $http } = useGlobal()
    expect(store.current_user?.user_id).toBe('test-user-id')
    expect(store.user_api_key).toBeDefined()
    expect($http.value.defaults.headers.common['X-Api-Key']).toBe(store.user_api_key)
    expect(localStorage.getItem('storytangl.player-secret')).toBe(store.user_secret)
  })

  it('rotates the authenticated user secret through the query-parameter route', async () => {
    const store = useStore()
    await store.authenticateWithSecret(store.user_secret)
    await store.rotateSecret('new-secret-123')

    const { $http } = useGlobal()
    expect(store.user_secret).toBe('new-secret-123')
    expect(store.user_api_key).toBeDefined()
    expect($http.value.defaults.headers.common['X-Api-Key']).toBe(store.user_api_key)
    expect(localStorage.getItem('storytangl.player-secret')).toBe('new-secret-123')
  })

  describe('world preferences', () => {
    const requests: string[] = []
    const serveRepartee = () =>
      server.use(
        http.get(`${DEFAULT_API_URL}/world/repartee_loop/info`, ({ request }) => {
          const url = new URL(request.url)
          requests.push(url.search)
          return HttpResponse.json(
            url.searchParams.get('channels') === 'ui-stage,ui-preferences'
              ? reparteePresentationInfo
              : reparteeWorldCatalog
          )
        })
      )

    beforeEach(() => {
      requests.length = 0
    })

    it('fetches the advertised stage and preferences, starting from defaults', async () => {
      serveRepartee()
      const store = useStore()
      store.current_world_uid = 'repartee_loop'
      expect(store.stage_extent).toEqual({ width: 320, height: 200 })
      await store.getWorldPresentation('repartee_loop')

      expect(requests).toEqual(['', '?channels=ui-stage,ui-preferences'])
      expect(store.stage_extent).toEqual({ width: 320, height: 200 })
      expect(store.world_preferences.map((item) => item.id)).toEqual([
        'sprites-visible',
        'clerk-motion',
      ])
      expect(store.preference_values).toEqual({
        'sprites-visible': true,
        'clerk-motion': 'idle',
      })
    })

    it("takes the world's declared stage extent", async () => {
      server.use(
        http.get(`${DEFAULT_API_URL}/world/wide/info`, ({ request }) =>
          HttpResponse.json(
            new URL(request.url).searchParams.has('channels')
              ? {
                  channels: [],
                  sections: [
                    {
                      section_id: 'ui-stage',
                      title: 'Stage extent',
                      value: { value_type: 'stage_extent', width: 640, height: 400 },
                    },
                  ],
                }
              : { channels: [{ channel_id: 'ui-stage', shortcuts: [] }], sections: [] }
          )
        )
      )
      const store = useStore()
      store.current_world_uid = 'wide'
      await store.getWorldPresentation('wide')

      expect(store.stage_extent).toEqual({ width: 640, height: 400 })
      expect(store.world_preferences).toEqual([])
    })

    it('asks only for channels the world advertises', async () => {
      const store = useStore()
      await store.getWorldPresentation('tangl_world')

      expect(store.world_preferences).toEqual([])
      expect(store.preference_values).toEqual({})
    })

    it('keeps values in this browser per world, never in a request', async () => {
      serveRepartee()
      const store = useStore()
      store.current_world_uid = 'repartee_loop'
      await store.getWorldPresentation('repartee_loop')
      requests.length = 0

      store.setPreference('clerk-motion', 'call')
      store.setPreference('sprites-visible', false)

      expect(requests).toEqual([])
      expect(JSON.parse(localStorage.getItem('storytangl.ui-preferences.repartee_loop')!)).toEqual(
        { 'sprites-visible': false, 'clerk-motion': 'call' }
      )
      store.preference_values = {}
      await store.getWorldPresentation('repartee_loop')
      expect(store.preference_values).toEqual({
        'sprites-visible': false,
        'clerk-motion': 'call',
      })
    })

    it('resets a stored value the world no longer declares', async () => {
      serveRepartee()
      localStorage.setItem(
        'storytangl.ui-preferences.repartee_loop',
        JSON.stringify({ 'sprites-visible': 'yes', 'clerk-motion': 'dance' })
      )
      const store = useStore()
      store.current_world_uid = 'repartee_loop'
      await store.getWorldPresentation('repartee_loop')

      expect(store.preference_values).toEqual({
        'sprites-visible': true,
        'clerk-motion': 'idle',
      })
    })
  })
})
