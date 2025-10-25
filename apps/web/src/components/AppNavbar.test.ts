import { afterEach, beforeEach, describe, it, expect, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { setActivePinia, createPinia } from 'pinia'

import AppNavbar from './AppNavbar.vue'
import WorldInfo from '@/components/dialogs/WorldInfo.vue'
import { useStore } from '@/store'

const vuetify = createVuetify({ components, directives })
const DEFAULT_API_URL = 'http://localhost:8000/api/v2'

describe('AppNavbar', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.unstubAllEnvs()
    vi.stubEnv('VITE_DEFAULT_API_URL', DEFAULT_API_URL)
    vi.spyOn(window, 'open').mockImplementation(() => null)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  const mountNavbar = () =>
    mount(
      {
        components: { AppNavbar },
        template: '<v-app><AppNavbar /></v-app>',
      },
      {
        global: { plugins: [vuetify] },
      },
    )

  it('displays app title', () => {
    const wrapper = mountNavbar()
    expect(wrapper.text()).toContain('WebTangl')
  })

  it('has menu toggle button', () => {
    const wrapper = mountNavbar()
    const menuBtn = wrapper.find('[aria-label="menu"]')
    expect(menuBtn.exists()).toBe(true)
  })

  it('emits toggle-drawer when menu button clicked', async () => {
    const wrapper = mountNavbar()
    const navbar = wrapper.findComponent(AppNavbar)
    const menuBtn = navbar.find('button')
    await menuBtn.trigger('click')

    expect(navbar.emitted('toggle-drawer')).toBeTruthy()
  })

  it('fetches and displays world list', async () => {
    const wrapper = mountNavbar()
    await flushPromises()

    const worldsBtn = wrapper.findAll('button').find((button) => button.text().includes('Worlds'))
    expect(worldsBtn).toBeDefined()
  })

  it('has user and info menu buttons', () => {
    const wrapper = mountNavbar()
    const buttons = wrapper.findAll('button').map((button) => button.text())
    expect(buttons.some((text) => text.includes('User'))).toBe(true)
    expect(buttons.some((text) => text.includes('Info'))).toBe(true)
  })

  it('fetches world info on mount', async () => {
    const wrapper = mountNavbar()
    await flushPromises()

    const store = useStore()
    expect(store.current_world_info).toBeDefined()
    expect(wrapper.findComponent(WorldInfo).exists()).toBe(true)
  })
})
