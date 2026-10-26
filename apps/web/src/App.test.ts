import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { setActivePinia, createPinia } from 'pinia'

import App from '@/App.vue'
import AppNavbar from '@/components/AppNavbar.vue'
import StoryFlow from '@/components/story/StoryFlow.vue'
import { useGlobal } from '@/composables/globals'
import StoryBlock from '@/components/story/StoryBlock.vue'
import { useStore } from '@/store'
import { HttpResponse, http, server } from '@tests/setup'
import {
  crossroadsRuntimeEnvelope,
  crossroadsNextRuntimeEnvelope,
  sandboxInfoState,
  sandboxProjectedState,
} from '@tests/fixtures'
import { mockUserInfo } from '@tests/mocks/mockData'

const vuetify = createVuetify({ components, directives })
const DEFAULT_API_URL = 'http://localhost:8000/api/v2'

describe('App.vue', () => {
  beforeEach(() => {
    server.use(
      http.get(`${DEFAULT_API_URL}/user/info`, () =>
        HttpResponse.json({
          ...mockUserInfo,
          current_ledger_id: 'ledger-1',
        })
      )
    )
    setActivePinia(createPinia())
    vi.unstubAllEnvs()
    vi.stubEnv('VITE_DEFAULT_API_URL', DEFAULT_API_URL)
    vi.stubEnv('VITE_DEFAULT_USER_SECRET', 'dev-secret-123')
    vi.resetModules()
    vi.spyOn(window, 'open').mockImplementation(() => null)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  const mountApp = () =>
    mount(App, {
      global: {
        plugins: [vuetify],
      },
    })

  it('gates new players until explicit creation, serializes creation, and uses response identity', async () => {
    server.use(http.get(`${DEFAULT_API_URL}/user/info`, () => HttpResponse.json(mockUserInfo)))
    const read = vi.spyOn(useGlobal().$http.value, 'get')
    let release!: () => void
    let creations = 0
    server.use(
      http.post(`${DEFAULT_API_URL}/story/create`, () => {
        creations += 1
        return new Promise((resolve) => {
          release = () =>
            resolve(
              HttpResponse.json({
                ...crossroadsRuntimeEnvelope,
                metadata: { world_id: 'actual-world', ledger_id: 'actual-ledger' },
              })
            )
        })
      })
    )
    const wrapper = mountApp()
    await flushPromises()
    expect(wrapper.findComponent(StoryFlow).exists()).toBe(false)
    expect(read.mock.calls.some(([url]) => /\/story\/(update|info)/.test(String(url)))).toBe(false)
    const navbar = wrapper.findComponent(AppNavbar)
    navbar.vm.$emit('select-world', 'requested-world')
    navbar.vm.$emit('select-world', 'requested-world')
    await flushPromises()
    expect(navbar.props('busy')).toBe(true)
    expect(creations).toBe(1)
    release()
    await flushPromises()
    expect(useStore().current_world_uid).toBe('actual-world')
    expect(useStore().current_user?.current_ledger_id).toBe('actual-ledger')
    expect(wrapper.findAllComponents(StoryFlow)).toHaveLength(1)
    expect(read.mock.calls.some(([url]) => String(url) === '/story/update')).toBe(false)
  })

  it('reports creation failure and checks current state before permitting another write', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    server.use(
      http.get(`${DEFAULT_API_URL}/user/info`, () => HttpResponse.json(mockUserInfo)),
      http.post(`${DEFAULT_API_URL}/story/create`, () =>
        HttpResponse.json({ detail: 'failed' }, { status: 500 })
      )
    )
    const wrapper = mountApp()
    await flushPromises()
    wrapper.findComponent(AppNavbar).vm.$emit('select-world', 'reference')
    await flushPromises()
    expect(wrapper.text()).toContain('Story creation failed')
    expect(wrapper.findComponent(StoryFlow).exists()).toBe(false)
    expect(wrapper.findComponent(AppNavbar).props('busy')).toBe(true)
    const retry = wrapper
      .findAll('button')
      .find((button) => button.text().includes('Retry current story'))!
    await retry.trigger('click')
    await flushPromises()
    expect(wrapper.findComponent(AppNavbar).props('busy')).toBe(false)
  })

  it('keeps a failed stored-user resume visible without creating a replacement', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    let creations = 0
    server.use(
      http.get(`${DEFAULT_API_URL}/story/update`, () =>
        HttpResponse.json({ detail: 'missing ledger' }, { status: 400 })
      ),
      http.post(`${DEFAULT_API_URL}/story/create`, () => {
        creations += 1
        return HttpResponse.json(crossroadsRuntimeEnvelope)
      })
    )
    const wrapper = mountApp()
    await flushPromises()
    expect(wrapper.text()).toContain('Unable to continue the current story')
    expect(wrapper.findComponent(StoryFlow).exists()).toBe(false)
    expect(creations).toBe(0)
  })

  it('does not repopulate a new session from a late history read', async () => {
    let release!: () => void
    let reads = 0
    server.use(
      http.get(`${DEFAULT_API_URL}/story/update`, () => {
        reads += 1
        return new Promise((resolve) => {
          release = () => resolve(HttpResponse.json(crossroadsRuntimeEnvelope))
        })
      })
    )
    const previous = mountApp()
    await flushPromises()
    previous.unmount()
    server.use(http.get(`${DEFAULT_API_URL}/user/info`, () => HttpResponse.json(mockUserInfo)))
    const current = mountApp()
    await flushPromises()
    release()
    await flushPromises()
    expect(current.findComponent(StoryFlow).exists()).toBe(false)
    expect(current.text()).toContain('Choose a world')
    expect(reads).toBe(1)
  })

  it('retires reconciliation progress, preserves refusal, and clears it after a successful move', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    let submissions = 0
    let creations = 0
    server.use(
      http.post(`${DEFAULT_API_URL}/story/create`, () => {
        creations += 1
        return HttpResponse.json(crossroadsRuntimeEnvelope)
      }),
      http.post(`${DEFAULT_API_URL}/story/do`, () => {
        submissions += 1
        return submissions === 1
          ? HttpResponse.json({ detail: 'A permit is required.' }, { status: 400 })
          : HttpResponse.json(crossroadsNextRuntimeEnvelope)
      })
    )
    const wrapper = mountApp()
    await flushPromises()
    const scene = wrapper.findComponent(StoryBlock)
    scene.vm.$emit('doAction', 'e-crossroads-03-bargain')
    scene.vm.$emit('doAction', 'e-crossroads-03-bargain')
    await flushPromises()
    expect(submissions).toBe(1)
    expect(wrapper.text()).toContain('A permit is required.')
    expect(wrapper.text()).not.toContain('Checking the current story')
    expect(wrapper.findComponent(AppNavbar).props('busy')).toBe(false)
    wrapper.findComponent(StoryBlock).vm.$emit('doAction', 'e-crossroads-03-bargain')
    await flushPromises()
    expect(wrapper.text()).toContain('The stranger slides the folded vellum')
    expect(wrapper.text()).not.toContain('A permit is required.')
    expect(submissions).toBe(2)
    expect(creations).toBe(0)
  })

  it('retains a failed reconciliation and blocks writes without a replacement story', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    let submissions = 0
    let creations = 0
    const wrapper = mountApp()
    await flushPromises()
    server.use(
      http.post(`${DEFAULT_API_URL}/story/do`, () => {
        submissions += 1
        return HttpResponse.error()
      }),
      http.get(`${DEFAULT_API_URL}/story/update`, () =>
        HttpResponse.json({ detail: 'Unavailable' }, { status: 500 })
      ),
      http.post(`${DEFAULT_API_URL}/story/create`, () => {
        creations += 1
        return HttpResponse.json(crossroadsRuntimeEnvelope)
      })
    )
    wrapper.findComponent(StoryBlock).vm.$emit('doAction', 'e-crossroads-03-bargain')
    await flushPromises()
    expect(wrapper.text()).toContain('Unable to continue the current story')
    expect(wrapper.text()).not.toContain('Checking the current story')
    expect(wrapper.findComponent(StoryFlow).exists()).toBe(false)
    expect(wrapper.findComponent(AppNavbar).props('busy')).toBe(true)
    wrapper.findComponent(AppNavbar).vm.$emit('select-world', 'reference')
    await flushPromises()
    expect(submissions).toBe(1)
    expect(creations).toBe(0)
  })

  it('clears story and status on a player switch', async () => {
    const wrapper = mountApp()
    await flushPromises()
    expect(wrapper.findComponent(StoryFlow).exists()).toBe(true)
    wrapper.findComponent(AppNavbar).vm.$emit('recover-player')
    await flushPromises()
    expect(wrapper.findComponent(StoryFlow).exists()).toBe(false)
    expect(wrapper.find('.v-navigation-drawer').exists()).toBe(false)
    expect(useStore().current_world_uid).toBe('')
  })

  it('renders the full application shell', async () => {
    const wrapper = mountApp()
    await flushPromises()

    expect(wrapper.find('.v-app-bar').exists()).toBe(true)
    expect(wrapper.find('.v-navigation-drawer').exists()).toBe(true)
    expect(wrapper.find('.v-main').exists()).toBe(true)
    expect(wrapper.find('.v-footer').exists()).toBe(true)
  })

  it('waits for authentication before mounting API-backed children', async () => {
    let resolveAuthentication: (() => void) | undefined
    const store = useStore()
    store.user_secret = 'delayed-secret'
    vi.spyOn(store, 'authenticateWithSecret').mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          resolveAuthentication = resolve
        })
    )

    const wrapper = mountApp()
    await flushPromises()

    expect(wrapper.find('[data-testid="storyflow-progress"]').exists()).toBe(false)
    expect(wrapper.find('.v-app-bar').exists()).toBe(false)

    resolveAuthentication?.()
    await flushPromises()

    expect(wrapper.find('.v-app-bar').exists()).toBe(true)
  })

  it('restores the browser-local player secret before any configured default', async () => {
    const store = useStore()
    store.user_secret = 'configured-secret'
    localStorage.setItem('storytangl.player-secret', 'returning-secret')
    vi.spyOn(store, 'authenticateWithSecret').mockResolvedValue()

    mountApp()
    await flushPromises()

    expect(store.authenticateWithSecret).toHaveBeenCalledWith('returning-secret')
  })

  it('keeps API-backed children at the gate when an existing secret is invalid', async () => {
    const store = useStore()
    store.user_secret = ''
    localStorage.setItem('storytangl.player-secret', 'invalid-secret')
    vi.spyOn(console, 'error').mockImplementation(() => undefined)
    server.use(
      http.get(`${DEFAULT_API_URL}/user/info`, () =>
        HttpResponse.json({ detail: 'Invalid API key' }, { status: 401 })
      )
    )

    const wrapper = mountApp()
    await flushPromises()

    expect(wrapper.find('[data-testid="authentication-error"]').exists()).toBe(true)
    expect(wrapper.find('.v-app-bar').exists()).toBe(false)
    expect(localStorage.getItem('storytangl.player-secret')).toBeNull()
  })

  it('mounts API-backed children after authenticating an existing secret', async () => {
    const store = useStore()
    store.user_secret = ''
    localStorage.setItem('storytangl.player-secret', 'invalid-secret')
    vi.spyOn(console, 'error').mockImplementation(() => undefined)
    server.use(
      http.get(`${DEFAULT_API_URL}/user/info`, () =>
        HttpResponse.json({ detail: 'Invalid API key' }, { status: 401 })
      )
    )

    const wrapper = mountApp()
    await flushPromises()

    server.resetHandlers()

    await wrapper.find('[data-testid="authentication-secret"] input').setValue('valid-secret')
    await wrapper.find('[data-testid="authentication-existing"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('.v-app-bar').exists()).toBe(true)
    expect(store.current_user?.user_id).toBe('test-user-id')
  })

  it('does not mint a player when an invalid recovery secret is entered', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const store = useStore()
    store.user_secret = 'unknown-recovery-secret'
    let creations = 0
    server.use(
      http.get(`${DEFAULT_API_URL}/user/info`, () =>
        HttpResponse.json({ detail: 'Invalid API key' }, { status: 401 })
      ),
      http.post(`${DEFAULT_API_URL}/user/create`, () => {
        creations += 1
        return HttpResponse.json({ api_key: 'invalid', user_secret: 'unknown-recovery-secret' })
      })
    )
    const wrapper = mountApp()
    await flushPromises()
    await wrapper
      .get('[data-testid="authentication-secret"] input')
      .setValue('unknown-recovery-secret')
    await wrapper.get('[data-testid="authentication-existing"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-testid="authentication-error"]').exists()).toBe(true)
    expect(wrapper.findComponent(StoryFlow).exists()).toBe(false)
    expect(creations).toBe(0)
  })

  it('silently creates and stores a player on first visit', async () => {
    const store = useStore()
    store.user_secret = ''

    const wrapper = mountApp()
    await flushPromises()

    expect(wrapper.find('.v-app-bar').exists()).toBe(true)
    expect(store.user_secret).not.toBe('')
    expect(localStorage.getItem('storytangl.player-secret')).toBe(store.user_secret)
  })

  it('toggles drawer when menu clicked', async () => {
    const wrapper = mountApp()
    await flushPromises()

    const navButton = wrapper.find('[aria-label="menu"]')
    expect(navButton.exists()).toBe(true)

    const initialState = (wrapper.vm as any).drawer
    await navButton.trigger('click')
    expect((wrapper.vm as any).drawer).toBe(!initialState)
  })

  it('loads story content on mount', async () => {
    const wrapper = mountApp()
    await flushPromises()

    const blocks = wrapper.findAll('.v-card')
    expect(blocks.length).toBeGreaterThan(0)
  })

  it('loads status items in drawer', async () => {
    const wrapper = mountApp()
    await flushPromises()

    const drawer = wrapper.find('.v-navigation-drawer')
    expect(drawer.text()).toContain('Status')
    expect(drawer.text()).toContain('Wounds')
    expect(drawer.text()).toContain('Purse')
    expect(drawer.text()).toContain('Sound')
  })

  it('discovers story-info affordances independently of runtime envelopes', async () => {
    server.use(
      http.get(`${DEFAULT_API_URL}/story/update`, () =>
        HttpResponse.json({
          ...crossroadsRuntimeEnvelope,
          metadata: {
            ...crossroadsRuntimeEnvelope.metadata,
            info_state: sandboxInfoState,
          },
        })
      ),
      http.get(`${DEFAULT_API_URL}/story/info`, () => HttpResponse.json(sandboxProjectedState))
    )

    const wrapper = mountApp()
    await flushPromises()

    const drawer = wrapper.find('.v-navigation-drawer')
    expect(drawer.text()).toContain('Map')
    expect(drawer.text()).toContain('Carrying')
    expect(drawer.text()).toContain('Help')
  })
})
