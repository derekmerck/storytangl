import { afterEach, beforeEach, describe, it, expect, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { setActivePinia, createPinia } from 'pinia'

import AppNavbar from './AppNavbar.vue'
import WorldInfo from '@/components/dialogs/WorldInfo.vue'
import { useStore } from '@/store'
import { useGlobal } from '@/composables/globals'
import { http, HttpResponse, server } from '@tests/setup'

const vuetify = createVuetify({ components, directives })
const DEFAULT_API_URL = 'http://localhost:8000/api/v2'

describe('AppNavbar', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    useStore().current_world_uid = 'tangl_world'
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
      }
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

  it('uses catalog labels and titles, emits explicit selection, and performs no user/world write', async () => {
    const put = vi.spyOn(useGlobal().$http.value, 'put')
    const wrapper = mount(AppNavbar, {
      global: {
        plugins: [vuetify],
        stubs: {
          VAppBar: { template: '<header><slot/></header>' },
          VMenu: {
            template: '<div><slot name="activator" :props="{}"/><slot/></div>',
          },
        },
      },
    })
    await flushPromises()
    expect(wrapper.text()).toContain('Tangl World')
    expect(wrapper.text()).toContain('Anonymous Stories')
    await wrapper
      .findAll('.v-list-item')
      .find((item) => item.text() === 'Solarpunk Stories')!
      .trigger('click')
    expect(wrapper.emitted('select-world')).toEqual([['solarpunk']])
    expect(put).not.toHaveBeenCalled()
    await wrapper.setProps({ busy: true })
    expect(
      wrapper
        .findAll('button')
        .find((button) => button.text() === 'Worlds')!
        .attributes('disabled')
    ).toBeDefined()
  })

  it('shows a catalog failure and an empty catalog honestly', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    server.use(http.get(`${DEFAULT_API_URL}/system/worlds`, () => HttpResponse.json([])))
    const wrapper = mount(AppNavbar, {
      global: {
        plugins: [vuetify],
        stubs: {
          VAppBar: { template: '<header><slot/></header>' },
          VMenu: {
            template: '<div><slot name="activator" :props="{}"/><slot/></div>',
          },
        },
      },
    })
    await flushPromises()
    expect(wrapper.text()).toContain('No worlds available')
    wrapper.unmount()
    server.use(
      http.get(`${DEFAULT_API_URL}/system/worlds`, () => HttpResponse.json({}, { status: 500 }))
    )
    const failed = mount(AppNavbar, {
      global: {
        plugins: [vuetify],
        stubs: {
          VAppBar: { template: '<header><slot/></header>' },
          VMenu: {
            template: '<div><slot name="activator" :props="{}"/><slot/></div>',
          },
        },
      },
    })
    await flushPromises()
    expect(failed.text()).toContain('Unable to load worlds')
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
