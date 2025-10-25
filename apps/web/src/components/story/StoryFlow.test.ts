import { beforeAll, beforeEach, afterEach, afterAll, describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { http, HttpResponse } from 'msw'

import { server } from '@tests/setup'
import { mockBlock1, mockBlock2 } from '@tests/mocks/mockData'

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
  it('shows a loading indicator while fetching initial blocks', async () => {
    let resolveResponse!: () => void
    let notifyHandlerReady!: () => void
    const handlerInvoked = new Promise<void>((resolve) => {
      notifyHandlerReady = resolve
    })

    server.use(
      http.get(`${DEFAULT_API_URL}/story/update`, () =>
        new Promise((resolve) => {
          notifyHandlerReady()
          resolveResponse = () => resolve(HttpResponse.json([mockBlock1, mockBlock2]))
        }),
      ),
    )

    const wrapper = mountFlow()
    const component = wrapper.findComponent(StoryFlow)
    const vm = component.vm as unknown as { loading: boolean }

    await handlerInvoked
    await flushPromises()
    await nextTick()
    await flushPromises()
    await nextTick()

    expect(vm.loading).toBe(true)
    expect(wrapper.find('[data-testid="storyflow-progress"]').exists()).toBe(true)

    resolveResponse()

    await new Promise((resolve) => setTimeout(resolve, 0))
    await flushPromises()
    await nextTick()
    await (component.vm as any).$nextTick?.()

    expect(vm.loading).toBe(false)

    await new Promise<void>((resolve, reject) => {
      const start = Date.now()
      const check = () => {
        if (!wrapper.find('[data-testid="storyflow-progress"]').exists()) {
          resolve()
          return
        }

        if (Date.now() - start > 1000) {
          reject(new Error('progress indicator still visible'))
          return
        }

        setTimeout(check, 10)
      }

      check()
    })
  })

  it('fetches and renders initial blocks on mount', async () => {
    const wrapper = mountFlow()
    await flushPromises()

    const blocks = wrapper.findAllComponents(StoryBlock)
    expect(blocks.length).toBeGreaterThan(0)
  })

  it('assigns unique keys to blocks', async () => {
    const wrapper = mountFlow()
    await flushPromises()

    const blocks = wrapper.findAllComponents(StoryBlock)
    const keys = blocks.map((b) => (b.props('block') as any).key)
    const uniqueKeys = new Set(keys)
    expect(keys.length).toBe(uniqueKeys.size)
  })

  it('remaps media URLs in blocks', async () => {
    const wrapper = mountFlow()
    await flushPromises()

    const block = wrapper
      .findAllComponents(StoryBlock)
      .map((b) => b.props('block') as typeof mockBlock1)
      .find((b) => b.media_dict?.narrative_im)

    if (block?.media_dict?.narrative_im) {
      expect(block.media_dict.narrative_im.url).toMatch(/^http/)
    }
  })

  it('creates media_dict for blocks with media', async () => {
    const wrapper = mountFlow()
    await flushPromises()

    const block = wrapper
      .findAllComponents(StoryBlock)
      .map((b) => b.props('block') as typeof mockBlock1)
      .find((b) => Array.isArray(b.media) && b.media.length > 0)

    if (block) {
      expect(block.media_dict).toBeDefined()
    }
  })

  it('remaps URLs in dialog block media', async () => {
    const wrapper = mountFlow()
    await flushPromises()

    const block = wrapper
      .findAllComponents(StoryBlock)
      .map((b) => b.props('block') as typeof mockBlock2)
      .find((b) => b.dialog?.some((dialog) => dialog.media_dict?.avatar_im))

    if (block) {
      const dialog = block.dialog?.find((d) => d.media_dict?.avatar_im)
      if (dialog?.media_dict?.avatar_im) {
        expect(dialog.media_dict.avatar_im.url).toMatch(/^http/)
      }
    }
  })

  it('clears blocks and resets when label is present', async () => {
    const wrapper = mountFlow()
    await flushPromises()

    const initialCount = wrapper.findAllComponents(StoryBlock).length
    expect(initialCount).toBeGreaterThan(0)

    server.use(
      http.post(`${DEFAULT_API_URL}/story/do`, () =>
        HttpResponse.json([
          { ...mockBlock1, uid: 'reset-block', label: 'Reset scene', text: 'New beginning' },
        ]),
      ),
    )

    const firstBlock = wrapper.findComponent(StoryBlock)
    await firstBlock.vm.$emit('doAction', firstBlock.props('block'), 'action_uid', null)
    await flushPromises()

    const blocks = wrapper.findAllComponents(StoryBlock)
    expect(blocks).toHaveLength(1)
    const [onlyBlock] = blocks
    expect(onlyBlock).toBeDefined()
    expect((onlyBlock!.props('block') as any).uid).toBe('reset-block')
  })

  it('calls API on doAction and appends new blocks', async () => {
    server.use(
      http.post(`${DEFAULT_API_URL}/story/do`, () =>
        HttpResponse.json([
          mockBlock1,
          { ...mockBlock2, uid: 'fresh-block', text: 'Another branch' },
        ]),
      ),
    )

    const wrapper = mountFlow()
    await flushPromises()
    const initialCount = wrapper.findAllComponents(StoryBlock).length

    const firstBlock = wrapper.findComponent(StoryBlock)
    await firstBlock.vm.$emit('doAction', firstBlock.props('block'), 'action_uid', null)
    await flushPromises()

    const blocks = wrapper.findAllComponents(StoryBlock)
    expect(blocks.length).toBeGreaterThan(initialCount)
  })

  it('increments block counter for each new block', async () => {
    const wrapper = mountFlow()
    await flushPromises()

    const keys = wrapper
      .findAllComponents(StoryBlock)
      .map((component) => (component.props('block') as any).key as string)

    keys.forEach((key) => {
      expect(key).toMatch(/-\d+$/)
    })
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
