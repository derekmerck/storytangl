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

    expect(wrapper.text()).toContain('status')
    expect(wrapper.text()).toContain('working')
  })

  it('applies custom styles when provided', async () => {
    const wrapper = mountStatus()
    await flushPromises()

    const styled = wrapper.findAll('[style]')
    expect(styled.length).toBeGreaterThan(0)
  })

  it('handles items without styles', async () => {
    const wrapper = mountStatus()
    await flushPromises()

    expect(wrapper.text()).toContain('unstyled')
  })

  it('displays icon when provided', async () => {
    const wrapper = mountStatus()
    await flushPromises()

    const icons = wrapper.findAll('.v-icon')
    expect(icons.length).toBeGreaterThanOrEqual(1)
  })

  it('handles empty status array', async () => {
    server.use(
      http.get(`${DEFAULT_API_URL}/story/status`, () => HttpResponse.json([])),
    )

    const wrapper = mountStatus()
    await flushPromises()

    expect(wrapper.text()).toContain('No status data available')
  })

  it('handles API error gracefully', async () => {
    server.use(http.get(`${DEFAULT_API_URL}/story/status`, () => HttpResponse.error()))

    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const wrapper = mountStatus()
    await flushPromises()

    expect(wrapper.text()).toContain('Unable to load story status')
    consoleSpy.mockRestore()
  })
})
