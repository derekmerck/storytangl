import { beforeEach, describe, it, expect, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

import StoryStatus from './StoryStatus.vue'
import { HttpResponse, http, server } from '@tests/setup'
import { sandboxInfoAffordances, sandboxInfoState, sandboxProjectedState } from '@tests/fixtures'

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
    server.use(
      http.get(`${DEFAULT_API_URL}/story/info`, () => HttpResponse.json(sandboxProjectedState)),
    )
    const wrapper = mountStatus()
    await flushPromises()

    expect(wrapper.find('[data-testid="info-affordance-bar"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Watch')
    expect(wrapper.text()).toContain('Map')
    expect(wrapper.text()).toContain('Carrying')
    expect(wrapper.text()).toContain('Help')
    const shortcuts = wrapper.findAll('.info-affordance-shortcut').map((node) => node.text())
    expect(shortcuts).toContain('m')
    expect(shortcuts).toContain('i')
  })

  it('treats info_state available channels as advisory affordance visibility', async () => {
    server.use(
      http.get(`${DEFAULT_API_URL}/story/info`, () => HttpResponse.json(sandboxProjectedState)),
    )
    const wrapper = mountStatus({
      infoState: { ...sandboxInfoState, available_channels: ['ui-map', 'ui-help'] },
    })
    await flushPromises()

    expect(wrapper.find('[data-info-channel="ui-map"]').exists()).toBe(true)
    expect(wrapper.find('[data-info-channel="ui-help"]').exists()).toBe(true)
    expect(wrapper.find('[data-info-channel="ui-inventory"]').exists()).toBe(false)
  })

  it('hides all affordances when info_state marks none available', async () => {
    server.use(
      http.get(`${DEFAULT_API_URL}/story/info`, () => HttpResponse.json(sandboxProjectedState)),
    )
    const wrapper = mountStatus({
      infoState: { ...sandboxInfoState, available_channels: [] },
    })
    await flushPromises()

    expect(wrapper.find('[data-testid="info-affordance-bar"]').exists()).toBe(false)
  })

  it('rediscovers the catalog when available channels change', async () => {
    let catalog: typeof sandboxInfoAffordances = [
      { channel_id: 'ui-sidebar', label: 'Status', shortcuts: [] },
    ]
    const seenChannels: Array<string | null> = []
    server.use(
      http.get(`${DEFAULT_API_URL}/story/info`, ({ request }) => {
        const channel = new URL(request.url).searchParams.get('channels')
        seenChannels.push(channel)
        if (channel === null) {
          return HttpResponse.json({ channels: catalog, sections: [] })
        }
        return HttpResponse.json({
          channels: [],
          sections: [
            {
              section_id: channel,
              title: channel,
              value: { value_type: 'scalar', value: channel },
            },
          ],
        })
      }),
    )
    const wrapper = mountStatus({
      refreshKey: 0,
      infoState: {
        version: 1,
        dirty_channels: ['ui-sidebar'],
        available_channels: ['ui-sidebar'],
      },
    })
    await flushPromises()

    catalog = [{ channel_id: 'ui-map', label: 'Map', shortcuts: ['m'] }]
    await wrapper.setProps({
      refreshKey: 1,
      infoState: {
        version: 2,
        dirty_channels: ['ui-map'],
        available_channels: ['ui-map'],
      },
    })
    await flushPromises()

    expect(seenChannels).toEqual([null, 'ui-sidebar', null, 'ui-map'])
    expect(wrapper.find('[data-info-channel="ui-map"]').exists()).toBe(true)
    expect(wrapper.find('[data-info-channel="ui-sidebar"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('ui-map')
  })

  it('selects a discovered channel when availability changes from empty', async () => {
    let catalog: typeof sandboxInfoAffordances = []
    const seenChannels: Array<string | null> = []
    server.use(
      http.get(`${DEFAULT_API_URL}/story/info`, ({ request }) => {
        const channel = new URL(request.url).searchParams.get('channels')
        seenChannels.push(channel)
        if (channel === null) {
          return HttpResponse.json({ channels: catalog, sections: [] })
        }
        return HttpResponse.json({
          channels: [],
          sections: [
            {
              section_id: channel,
              title: channel,
              value: { value_type: 'scalar', value: 'available now' },
            },
          ],
        })
      }),
    )
    const wrapper = mountStatus({
      refreshKey: 0,
      infoState: { version: 1, dirty_channels: [], available_channels: [] },
    })
    await flushPromises()

    catalog = [{ channel_id: 'ui-help', label: 'Help', shortcuts: ['?'] }]
    await wrapper.setProps({
      refreshKey: 1,
      infoState: {
        version: 2,
        dirty_channels: ['ui-help'],
        available_channels: ['ui-help'],
      },
    })
    await flushPromises()

    expect(seenChannels).toEqual([null, null, 'ui-help'])
    expect(wrapper.find('[data-info-channel="ui-help"]').attributes('aria-pressed')).toBe('true')
    expect(wrapper.text()).toContain('available now')
  })

  it('loads the selected exact story-info channel', async () => {
    const seenParams: URLSearchParams[] = []
    server.use(
      http.get(`${DEFAULT_API_URL}/story/info`, ({ request }) => {
        seenParams.push(new URL(request.url).searchParams)
        return HttpResponse.json(sandboxProjectedState)
      }),
    )

    const wrapper = mountStatus()
    await flushPromises()

    const mapButton = wrapper.find('[data-info-channel="ui-map"]')
    expect(mapButton.exists()).toBe(true)
    await mapButton.trigger('click')
    await flushPromises()

    expect(seenParams.at(0)?.toString()).toBe('')
    const mapParams = seenParams.find((params) => params.get('channels') === 'ui-map')
    expect(mapParams).toBeDefined()
    expect(mapParams?.has('kind')).toBe(false)
    expect(mapParams?.has('query')).toBe(false)
  })

  it('ignores stale story-info responses when affordance requests overlap', async () => {
    type StoryInfoResponse = { channels?: typeof sandboxInfoAffordances; sections: Array<Record<string, unknown>> }
    const pending = new Map<string, unknown>()
    server.use(
      http.get(`${DEFAULT_API_URL}/story/info`, ({ request }) => {
        const channel = new URL(request.url).searchParams.get('channels')
        if (channel === null) {
          return HttpResponse.json({ channels: sandboxInfoAffordances, sections: [] })
        }
        return new Promise((resolve) => {
          pending.set(channel, (payload: StoryInfoResponse) => resolve(HttpResponse.json(payload)))
        })
      }),
    )

    const wrapper = mountStatus()
    await flushPromises()

    await wrapper.find('[data-info-channel="ui-map"]').trigger('click')
    await flushPromises()

    const resolveMap = pending.get('ui-map')
    if (typeof resolveMap === 'function') {
      resolveMap({
        sections: [
          {
            section_id: 'map-result',
            title: 'Map Result',
            value: { value_type: 'scalar', value: 'new map' },
          },
        ],
      } satisfies StoryInfoResponse)
    }
    await flushPromises()

    const resolveStatus = pending.get('ui-world-time')
    if (typeof resolveStatus === 'function') {
      resolveStatus({
        sections: [
          {
            section_id: 'status-result',
            title: 'Status Result',
            value: { value_type: 'scalar', value: 'stale status' },
          },
        ],
      } satisfies StoryInfoResponse)
    }
    await flushPromises()

    expect(wrapper.text()).toContain('new map')
    expect(wrapper.text()).not.toContain('stale status')
  })

  it('sends one exact channel without legacy query parameters', async () => {
    const seenParams: URLSearchParams[] = []
    server.use(
      http.get(`${DEFAULT_API_URL}/story/info`, ({ request }) => {
        seenParams.push(new URL(request.url).searchParams)
        return HttpResponse.json(sandboxProjectedState)
      }),
    )

    const wrapper = mountStatus()
    await flushPromises()

    await wrapper.find('[data-info-channel="ui-help"]').trigger('click')
    await flushPromises()

    const helpParams = seenParams.find((params) => params.get('channels') === 'ui-help')
    expect(helpParams).toBeDefined()
    expect(helpParams?.has('query')).toBe(false)
  })

  it('refreshes the projected status when the story update key changes', async () => {
    const statusHandler = vi.fn(({ request }) => {
      if (!new URL(request.url).searchParams.has('channels')) {
        return HttpResponse.json({
          channels: [{ channel_id: 'ui-sidebar', label: 'Status', shortcuts: [] }],
          sections: [],
        })
      }
      return HttpResponse.json({
        sections: [
          {
            section_id: 'turn',
            title: 'Turn',
            value: { value_type: 'scalar', value: statusHandler.mock.calls.length },
          },
        ],
      })
    })
    server.use(http.get(`${DEFAULT_API_URL}/story/info`, statusHandler))

    const wrapper = mountStatus({ refreshKey: 0 })
    await flushPromises()

    expect(statusHandler).toHaveBeenCalledTimes(2)

    await wrapper.setProps({ refreshKey: 1 })
    await flushPromises()

    expect(statusHandler).toHaveBeenCalledTimes(3)
    expect(wrapper.text()).toContain('3')
  })

  it('skips refreshes when info_state marks the active status channel clean', async () => {
    const statusHandler = vi.fn(({ request }) => {
      if (!new URL(request.url).searchParams.has('channels')) {
        return HttpResponse.json({
          channels: [{ channel_id: 'ui-sidebar', label: 'Status', shortcuts: [] }],
          sections: [],
        })
      }
      return HttpResponse.json({
        sections: [
          {
            section_id: 'turn',
            title: 'Turn',
            value: { value_type: 'scalar', value: statusHandler.mock.calls.length },
          },
        ],
      })
    })
    server.use(http.get(`${DEFAULT_API_URL}/story/info`, statusHandler))

    const wrapper = mountStatus({
      refreshKey: 0,
      infoState: { version: 17, dirty_channels: [], available_channels: ['ui-sidebar'] },
    })
    await flushPromises()

    expect(statusHandler).toHaveBeenCalledTimes(2)

    await wrapper.setProps({
      refreshKey: 1,
      infoState: { version: 18, dirty_channels: [], available_channels: ['ui-sidebar'] },
    })
    await flushPromises()

    expect(statusHandler).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('2')
  })

  it('refreshes when info_state marks the active status channel dirty', async () => {
    const statusHandler = vi.fn(({ request }) => {
      if (!new URL(request.url).searchParams.has('channels')) {
        return HttpResponse.json({
          channels: [{ channel_id: 'ui-sidebar', label: 'Status', shortcuts: [] }],
          sections: [],
        })
      }
      return HttpResponse.json({
        sections: [
          {
            section_id: 'turn',
            title: 'Turn',
            value: { value_type: 'scalar', value: statusHandler.mock.calls.length },
          },
        ],
      })
    })
    server.use(http.get(`${DEFAULT_API_URL}/story/info`, statusHandler))

    const wrapper = mountStatus({
      refreshKey: 0,
      infoState: { version: 17, dirty_channels: [], available_channels: ['ui-sidebar'] },
    })
    await flushPromises()

    await wrapper.setProps({
      refreshKey: 1,
      infoState: {
        version: 18,
        dirty_channels: ['ui-sidebar'],
        available_channels: ['ui-sidebar'],
      },
    })
    await flushPromises()

    expect(statusHandler).toHaveBeenCalledTimes(3)
    expect(wrapper.text()).toContain('3')
  })

  it('uses dirty channels for the selected info affordance', async () => {
    const seenChannels: string[] = []
    const statusHandler = vi.fn(({ request }) => {
      const channel = new URL(request.url).searchParams.get('channels')
      if (channel === null) {
        return HttpResponse.json({ channels: sandboxInfoAffordances, sections: [] })
      }
      seenChannels.push(channel)
      return HttpResponse.json({
        sections: [
          {
            section_id: channel,
            title: channel,
            value: { value_type: 'scalar', value: `${channel}-${seenChannels.length}` },
          },
        ],
      })
    })
    server.use(http.get(`${DEFAULT_API_URL}/story/info`, statusHandler))

    const wrapper = mountStatus({
      refreshKey: 0,
      infoState: { ...sandboxInfoState, dirty_channels: [] },
    })
    await flushPromises()

    await wrapper.find('[data-info-channel="ui-map"]').trigger('click')
    await flushPromises()

    await wrapper.setProps({
      refreshKey: 1,
      infoState: { ...sandboxInfoState, version: 18, dirty_channels: ['ui-inventory'] },
    })
    await flushPromises()

    expect(statusHandler).toHaveBeenCalledTimes(3)
    expect(seenChannels).toEqual(['ui-sidebar', 'ui-map'])
    expect(wrapper.text()).toContain('ui-map-2')

    await wrapper.setProps({
      refreshKey: 2,
      infoState: { ...sandboxInfoState, version: 19, dirty_channels: ['ui-map'] },
    })
    await flushPromises()

    expect(statusHandler).toHaveBeenCalledTimes(4)
    expect(seenChannels).toEqual(['ui-sidebar', 'ui-map', 'ui-map'])
    expect(wrapper.text()).toContain('ui-map-3')
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
