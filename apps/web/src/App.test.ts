import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { setActivePinia, createPinia } from 'pinia'

import App from '@/App.vue'

const vuetify = createVuetify({ components, directives })
const DEFAULT_API_URL = 'http://localhost:8000/api/v2'

describe('App.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.unstubAllEnvs()
    vi.stubEnv('VITE_DEFAULT_API_URL', DEFAULT_API_URL)
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

  it('renders the full application shell', async () => {
    const wrapper = mountApp()
    await flushPromises()

    expect(wrapper.find('.v-app-bar').exists()).toBe(true)
    expect(wrapper.find('.v-navigation-drawer').exists()).toBe(true)
    expect(wrapper.find('.v-main').exists()).toBe(true)
    expect(wrapper.find('.v-footer').exists()).toBe(true)
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
    expect(drawer.text()).toContain('working')
  })
})
