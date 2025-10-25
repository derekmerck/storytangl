import { afterEach, beforeEach, describe, it, expect, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { http, HttpResponse } from 'msw'

import SystemInfo from './SystemInfo.vue'
import { server } from '@/tests/setup'

const vuetify = createVuetify({ components, directives })
const DEFAULT_API_URL = 'http://localhost:8000/api/v2'

describe('SystemInfo', () => {
  beforeEach(() => {
    vi.unstubAllEnvs()
    vi.stubEnv('VITE_DEFAULT_API_URL', DEFAULT_API_URL)
    Object.defineProperty(globalThis, 'visualViewport', {
      value: {
        width: 1024,
        height: 768,
        scale: 1,
        offsetLeft: 0,
        offsetTop: 0,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      },
      configurable: true,
      writable: true,
    })
  })

  afterEach(() => {
    delete (globalThis as { visualViewport?: unknown }).visualViewport
  })

  const mountDialog = () =>
    mount(
      {
        components: { SystemInfo },
        template: '<v-app><SystemInfo model-value /></v-app>',
      },
      {
        global: {
          plugins: [vuetify],
          stubs: {
            teleport: true,
            transition: false,
            'v-dialog': {
              props: ['modelValue'],
              template: '<div v-if="modelValue" class="v-dialog"><slot /></div>',
            },
            'v-overlay': { template: '<div class="v-overlay"><slot /></div>' },
          },
        },
      },
    )

  it('fetches and displays system info when opened', async () => {
    const wrapper = mountDialog()
    await flushPromises()
    await flushPromises()

    const dialog = wrapper.findComponent(SystemInfo)
    expect(dialog.text()).toContain('System Information')
    expect(dialog.findAll('.v-list-item').length).toBeGreaterThan(0)
  })

  it('handles API errors gracefully', async () => {
    server.use(http.get(`${DEFAULT_API_URL}/system/info`, () => HttpResponse.error()))

    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const wrapper = mountDialog()
    await flushPromises()
    await flushPromises()

    const dialog = wrapper.findComponent(SystemInfo)
    expect(dialog.text()).toContain('Unable to load system information.')
    consoleSpy.mockRestore()
  })
})
