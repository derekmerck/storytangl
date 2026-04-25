import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

import { HttpResponse, http, server } from '@tests/setup'
import {
  crossroadsNextRuntimeEnvelope,
  crossroadsRuntimeEnvelope,
} from '@tests/fixtures'

const DEFAULT_API_URL = 'http://localhost:8000/api/v2'
const vuetify = createVuetify({ components, directives })

let StoryFlow: typeof import('./StoryFlow.vue')['default']
let StoryBlock: typeof import('./StoryBlock.vue')['default']
let originalScrollIntoView: typeof HTMLElement.prototype.scrollIntoView

beforeAll(() => {
  originalScrollIntoView = HTMLElement.prototype.scrollIntoView
  HTMLElement.prototype.scrollIntoView = vi.fn()
})

afterAll(() => {
  HTMLElement.prototype.scrollIntoView = originalScrollIntoView
})

beforeEach(async () => {
  vi.unstubAllEnvs()
  vi.stubEnv('VITE_DEFAULT_API_URL', DEFAULT_API_URL)
  vi.stubEnv('VITE_DEBUG', 'false')
  vi.stubEnv('VITE_VERBOSE', 'false')
  vi.resetModules()
  ;({ default: StoryFlow } = await import('./StoryFlow.vue'))
  ;({ default: StoryBlock } = await import('./StoryBlock.vue'))
})

afterEach(() => {
  vi.restoreAllMocks()
})

const mountFlow = () =>
  mount(StoryFlow, {
    global: {
      plugins: [vuetify],
      components: { StoryBlock },
    },
  })

describe('StoryFlow', () => {
  it('shows a loading indicator while fetching the initial envelope', async () => {
    let resolveResponse!: () => void
    let notifyHandlerReady!: () => void
    const handlerInvoked = new Promise<void>((resolve) => {
      notifyHandlerReady = resolve
    })

    server.use(
      http.get(`${DEFAULT_API_URL}/story/update`, () =>
        new Promise((resolve) => {
          notifyHandlerReady()
          resolveResponse = () => resolve(HttpResponse.json(crossroadsRuntimeEnvelope))
        }),
      ),
    )

    const wrapper = mountFlow()
    const component = wrapper.findComponent(StoryFlow)
    const vm = component.vm as unknown as { loading: boolean }

    await handlerInvoked
    await flushPromises()
    await nextTick()

    expect(vm.loading).toBe(true)
    expect(wrapper.find('[data-testid="storyflow-progress"]').exists()).toBe(true)

    resolveResponse()
    await flushPromises()
    await nextTick()

    expect(vm.loading).toBe(false)
  })

  it('fetches and renders scene groups on mount', async () => {
    const wrapper = mountFlow()
    await flushPromises()

    const scenes = wrapper.findAllComponents(StoryBlock)
    expect(scenes).toHaveLength(1)
    expect(wrapper.text()).toContain('Rain drums on the thatch')
    expect(wrapper.text()).toContain('Pay the forty silver')
  })

  it('renders canonical media fragments and remaps media URLs', async () => {
    const wrapper = mountFlow()
    await flushPromises()

    const imgs = wrapper.findAllComponents({ name: 'VImg' })
    const srcs = imgs.map((img) => String(img.props('src')))

    expect(srcs.some((src) => src === 'http://localhost:8000/media/world/tangl_world/stranger_booth.svg')).toBe(true)
  })

  it('renders locked choices, freeform choices, pending media, kv, and user events', async () => {
    const wrapper = mountFlow()
    await flushPromises()

    expect(wrapper.text()).toContain('Requires Sleight of Hand')
    expect(wrapper.find('input').exists()).toBe(true)
    expect(wrapper.find('[data-testid="pending-media"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('late evening')
    expect(wrapper.find('[data-testid="user-event"]').exists()).toBe(true)
  })

  it('applies control updates against the fragment registry', async () => {
    server.use(
      http.get(`${DEFAULT_API_URL}/story/update`, () =>
        HttpResponse.json({
          cursor_id: 'cursor-1',
          step: 1,
          fragments: [
            {
              uid: 'scene',
              fragment_type: 'group',
              group_type: 'scene',
              member_ids: ['content'],
            },
            {
              uid: 'content',
              fragment_type: 'content',
              content: 'Before update',
            },
            {
              uid: 'ctrl',
              fragment_type: 'update',
              ref_type: 'content',
              ref_id: 'content',
              payload: { content: 'After update' },
            },
          ],
        }),
      ),
    )

    const wrapper = mountFlow()
    await flushPromises()

    expect(wrapper.text()).toContain('After update')
    expect(wrapper.text()).not.toContain('Before update')
  })

  it('calls the API on doAction and appends returned scenes', async () => {
    server.use(
      http.post(`${DEFAULT_API_URL}/story/do`, async ({ request }) => {
        const body = await request.json()
        expect(body).toEqual({
          choice_id: 'edge-1',
          payload: { offer_silver: 12 },
        })
        return HttpResponse.json(crossroadsNextRuntimeEnvelope)
      }),
    )

    const wrapper = mountFlow()
    await flushPromises()

    const initialCount = wrapper.findAllComponents(StoryBlock).length
    const firstScene = wrapper.findComponent(StoryBlock)
    await firstScene.vm.$emit('doAction', 'edge-1', { offer_silver: 12 })
    await flushPromises()

    const scenes = wrapper.findAllComponents(StoryBlock)
    expect(scenes.length).toBeGreaterThan(initialCount)
    expect(wrapper.text()).toContain('The stranger slides the folded vellum')
  })

  it('handles unknown fragment types with visible fallbacks', async () => {
    server.use(
      http.get(`${DEFAULT_API_URL}/story/update`, () =>
        HttpResponse.json({
          cursor_id: 'cursor-1',
          step: 1,
          fragments: [
            {
              uid: 'mystery',
              fragment_type: 'dice_roll',
              content: { value: 6 },
            },
          ],
        }),
      ),
    )

    const wrapper = mountFlow()
    await flushPromises()

    expect(wrapper.find('[data-testid="fragment-fallback"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('dice_roll')
  })

  it('keeps referenced choice state visible for decision legibility', async () => {
    const wrapper = mountFlow()
    await flushPromises()

    expect(wrapper.text()).toContain('Show a card from your hand')
    expect(wrapper.text()).toContain('zone')
    expect(wrapper.text()).toContain('Rust map card')
  })

  it('adapts legacy JournalStoryUpdate arrays through a narrow compatibility path', async () => {
    server.use(
      http.get(`${DEFAULT_API_URL}/story/update`, () =>
        HttpResponse.json([
          {
            uid: 'legacy-block',
            text: '<p>Legacy text</p>',
            actions: [{ uid: 'legacy-choice', text: 'Legacy choice' }],
          },
        ]),
      ),
    )

    const wrapper = mountFlow()
    await flushPromises()

    expect(wrapper.html()).toContain('<p>Legacy text</p>')
    expect(wrapper.text()).toContain('Legacy choice')
  })

  it('handles API errors gracefully', async () => {
    server.use(
      http.get(`${DEFAULT_API_URL}/story/update`, () => HttpResponse.error()),
    )

    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const wrapper = mountFlow()
    await flushPromises()

    expect(wrapper.exists()).toBe(true)
    expect(wrapper.text()).toContain('Failed to load story')
    expect(consoleSpy).toHaveBeenCalled()
  })
})
