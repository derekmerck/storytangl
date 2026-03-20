import { beforeEach, describe, it, expect, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { http, HttpResponse } from 'msw'

import StoryStatus from './StoryStatus.vue'
import { server } from '@tests/setup'

const DEFAULT_API_URL = 'http://localhost:8000/api/v2'

const vuetify = createVuetify({ components, directives })

describe('StoryStatus', () => {
  beforeEach(async () => {
    vi.unstubAllEnvs()
    vi.stubEnv('VITE_DEFAULT_API_URL', DEFAULT_API_URL)
    vi.resetModules()
  })

  const mountStatus = () =>
    mount(StoryStatus, {
      global: {
        plugins: [vuetify],
      },
    })

  it('fetches and renders status items on mount', async () => {
    const wrapper = mountStatus()
    await flushPromises()

    const listItems = wrapper.findAll('.v-list-item')
    expect(listItems.length).toBeGreaterThan(0)
  })

  it('renders key-value pairs', async () => {
    const wrapper = mountStatus()
    await flushPromises()

    expect(wrapper.text()).toContain('Session')
    expect(wrapper.text()).toContain('Dark Forest')
  })

  it('renders projected section titles and values', async () => {
    const wrapper = mountStatus()
    await flushPromises()

    expect(wrapper.text()).toContain('Cursor')
    expect(wrapper.text()).toContain('Journal size')
  })

  it('renders custom section kinds generically', async () => {
    const wrapper = mountStatus()
    await flushPromises()

    expect(wrapper.text()).toContain('Flags')
    expect(wrapper.text()).toContain('torch_lit, met_guide')
  })

  it('handles empty status payload', async () => {
    server.use(
      http.get(`${DEFAULT_API_URL}/story/info`, () => HttpResponse.json({})),
    )

    const wrapper = mountStatus()
    await flushPromises()

    expect(wrapper.text()).toContain('No status data available')
  })

  it('handles API error gracefully', async () => {
    server.use(http.get(`${DEFAULT_API_URL}/story/info`, () => HttpResponse.error()))

    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const wrapper = mountStatus()
    await flushPromises()

    expect(wrapper.text()).toContain('Unable to load story status')
    consoleSpy.mockRestore()
  })
})
