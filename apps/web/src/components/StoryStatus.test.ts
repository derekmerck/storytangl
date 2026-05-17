import { beforeEach, describe, it, expect, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

import StoryStatus from './StoryStatus.vue'
import { HttpResponse, http, server } from '@tests/setup'
import { sandboxInfoAffordances, sandboxProjectedState } from '@tests/fixtures'

const DEFAULT_API_URL = 'http://localhost:8000/api/v2'

const vuetify = createVuetify({ components, directives })

describe('StoryStatus', () => {
  beforeEach(async () => {
    vi.unstubAllEnvs()
    vi.stubEnv('VITE_DEFAULT_API_URL', DEFAULT_API_URL)
    vi.resetModules()
  })

  const mountStatus = (props?: InstanceType<typeof StoryStatus>['$props']) =>
    mount(StoryStatus, {
      props,
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

    expect(wrapper.text()).toContain('Purse')
    expect(wrapper.text()).toContain('silver')
  })

  it('renders projected section titles and values', async () => {
    const wrapper = mountStatus()
    await flushPromises()

    expect(wrapper.text()).toContain('Wounds')
    expect(wrapper.text()).toContain('Sound')
    expect(wrapper.text()).toContain('Satchel')
  })

  it('renders custom section kinds generically', async () => {
    const wrapper = mountStatus()
    await flushPromises()

    expect(wrapper.text()).toContain('Conditions')
    expect(wrapper.text()).toContain('rain-soaked, hungry, hunted')
  })

  it('renders sandbox status conventions as generic projected sections', async () => {
    server.use(
      http.get(`${DEFAULT_API_URL}/story/info`, () => HttpResponse.json(sandboxProjectedState)),
    )

    const wrapper = mountStatus()
    await flushPromises()

    expect(wrapper.find('[data-section-kind="world_time"]').exists()).toBe(true)
    expect(wrapper.find('[data-section-kind="location"]').exists()).toBe(true)
    expect(wrapper.find('[data-section-kind="agenda"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('evening')
    expect(wrapper.text()).toContain('brass lamp')
    expect(wrapper.text()).toContain('fixture')
    expect(wrapper.text()).toContain('Guard changes watch')
  })

  it('renders optional info affordances without requiring bespoke client support', async () => {
    const wrapper = mountStatus({ infoAffordances: sandboxInfoAffordances })
    await flushPromises()

    expect(wrapper.find('[data-testid="info-affordance-bar"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Status')
    expect(wrapper.text()).toContain('Map')
    expect(wrapper.text()).toContain('Inventory')
    expect(wrapper.text()).toContain('Party')
    expect(wrapper.text()).toContain('m')
    expect(wrapper.text()).toContain('i')
  })

  it('loads the selected info affordance through story-info query params', async () => {
    const seenSearches: string[] = []
    server.use(
      http.get(`${DEFAULT_API_URL}/story/info`, ({ request }) => {
        seenSearches.push(new URL(request.url).search)
        return HttpResponse.json(sandboxProjectedState)
      }),
    )

    const wrapper = mountStatus({ infoAffordances: sandboxInfoAffordances })
    await flushPromises()

    const mapButton = wrapper.find('[data-info-kind="map"]')
    expect(mapButton.exists()).toBe(true)
    await mapButton.trigger('click')
    await flushPromises()

    expect(seenSearches[0]).toBe('')
    expect(seenSearches.some((search) => search.includes('type=map'))).toBe(true)
    expect(seenSearches.some((search) => search.includes('format=tiles'))).toBe(true)
  })

  it('uses the affordance kind as a fallback story-info type', async () => {
    const seenSearches: string[] = []
    server.use(
      http.get(`${DEFAULT_API_URL}/story/info`, ({ request }) => {
        seenSearches.push(new URL(request.url).search)
        return HttpResponse.json(sandboxProjectedState)
      }),
    )

    const wrapper = mountStatus({ infoAffordances: sandboxInfoAffordances })
    await flushPromises()

    await wrapper.find('[data-info-kind="inventory"]').trigger('click')
    await flushPromises()

    expect(seenSearches.some((search) => search.includes('type=inventory'))).toBe(true)
  })

  it('refreshes the projected status when the story update key changes', async () => {
    const statusHandler = vi.fn(() =>
      HttpResponse.json({
        sections: [
          {
            section_id: 'turn',
            title: 'Turn',
            value: { value_type: 'scalar', value: statusHandler.mock.calls.length },
          },
        ],
      }),
    )
    server.use(http.get(`${DEFAULT_API_URL}/story/info`, statusHandler))

    const wrapper = mountStatus({ refreshKey: 0 })
    await flushPromises()

    expect(statusHandler).toHaveBeenCalledTimes(1)

    await wrapper.setProps({ refreshKey: 1 })
    await flushPromises()

    expect(statusHandler).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('2')
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
