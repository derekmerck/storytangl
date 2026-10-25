import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import StoryFlow from './StoryFlow.vue'
import StoryBlock from './StoryBlock.vue'
import { isChoiceFragment } from './fragmentUtils'
import type { RuntimeEnvelope } from '@/types'
import { useGlobal } from '@/composables/globals'
import { HttpResponse, http, server } from '@tests/setup'
import { commandHintRuntimeEnvelope, crossroadsRuntimeEnvelope } from '@tests/fixtures'

const api = 'http://localhost:8000/api/v2'
const vuetify = createVuetify({ components, directives })
const mountFlow = (
  envelope = crossroadsRuntimeEnvelope,
  activeChoiceIds = envelope.fragments.filter(isChoiceFragment).map((item) => item.uid)
) =>
  mount(StoryFlow, {
    props: { initialEnvelope: envelope, activeChoiceIds },
    global: { plugins: [vuetify] },
  })
const offered: RuntimeEnvelope = {
  step: 1,
  fragments: [{ uid: 'choice', fragment_type: 'choice', edge_id: 'edge', text: 'Try' }],
}
beforeEach(() => {
  HTMLElement.prototype.scrollIntoView = vi.fn()
})
afterEach(() => {
  vi.restoreAllMocks()
})

describe('StoryFlow session rendering', () => {
  it('applies the initial envelope once without an update request', async () => {
    const read = vi.spyOn(useGlobal().$http.value, 'get')
    const wrapper = mountFlow()
    await flushPromises()
    expect(read).not.toHaveBeenCalled()
    expect(wrapper.findAllComponents(StoryBlock)).toHaveLength(1)
    expect(wrapper.text()).toContain('Rain drums on the thatch')
    expect(wrapper.text()).toContain('Pay the forty silver')
    expect(wrapper.emitted('storyUpdate')).toHaveLength(1)
    expect(
      wrapper
        .findAllComponents({ name: 'VImg' })
        .some((image) => String(image.props('src')).includes('/media/world/'))
    ).toBe(true)
    expect(wrapper.text()).toContain('Sleight of Hand 1, need 2.')
    expect(wrapper.find('[data-testid="pending-media"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('late evening')
    expect(wrapper.find('[data-testid="interrupt-ux-event"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="piece-fragment"]').exists()).toBe(true)
  })

  it('applies controls and retains unknown-fragment fallback', async () => {
    const wrapper = mountFlow({
      step: 1,
      fragments: [
        { uid: 'content', fragment_type: 'content', content: 'Before' },
        {
          uid: 'control',
          fragment_type: 'update',
          target: { kind: 'fragment', fragment_id: 'content' },
          payload: { content: 'After' },
        },
        { uid: 'unknown', fragment_type: 'new_unsupported_kind' },
      ],
    })
    await flushPromises()
    expect(wrapper.text()).toContain('After')
    expect(wrapper.text()).not.toContain('Before')
    expect(wrapper.text()).toContain('new_unsupported_kind')
  })

  it('keeps historical occurrences disabled when an edge is revisited', async () => {
    const envelope: RuntimeEnvelope = {
      step: 3,
      fragments: [
        { uid: 'old', fragment_type: 'choice', edge_id: 'reused', text: 'Historical visit' },
        { uid: 'new', fragment_type: 'choice', edge_id: 'reused', text: 'Current visit' },
      ],
    }
    const wrapper = mountFlow(envelope, ['new'])
    await flushPromises()
    const buttons = wrapper.findAll('button.choice-button')
    expect(buttons[0]!.attributes('disabled')).toBeDefined()
    expect(buttons[1]!.attributes('disabled')).toBeUndefined()
    expect(wrapper.findAll('.choice-row[data-hotkey]')).toHaveLength(1)
  })

  it('blocks repeat activation synchronously and preserves authored payload', async () => {
    let release!: () => void
    const submitted: unknown[] = []
    server.use(
      http.post(`${api}/story/do`, async ({ request }) => {
        submitted.push(await request.json())
        await new Promise<void>((resolve) => {
          release = resolve
        })
        return HttpResponse.json({
          step: 2,
          fragments: [{ uid: 'end', fragment_type: 'content', content: 'Advanced' }],
        })
      })
    )
    const wrapper = mountFlow(offered)
    await flushPromises()
    const scene = wrapper.findComponent(StoryBlock)
    scene.vm.$emit('doAction', 'edge', { offer_silver: 12 })
    scene.vm.$emit('doAction', 'edge', { offer_silver: 12 })
    await flushPromises()
    expect(submitted).toEqual([{ edge_id: 'edge', payload: { offer_silver: 12 } }])
    expect(wrapper.find('[data-testid="storyflow-progress"]').exists()).toBe(true)
    release()
    await flushPromises()
    expect(wrapper.text()).toContain('Advanced')
    expect(wrapper.find('button.choice-button').attributes('disabled')).toBeDefined()
  })

  it('preserves choices on refusal and requests resync on transport failure', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    server.use(http.post(`${api}/story/do`, () => HttpResponse.json({ step: 1, fragments: [] })))
    const wrapper = mountFlow(offered)
    await flushPromises()
    wrapper.findComponent(StoryBlock).vm.$emit('doAction', 'edge')
    await flushPromises()
    expect(wrapper.find('button.choice-button').attributes('disabled')).toBeUndefined()
    server.use(http.post(`${api}/story/do`, () => HttpResponse.error()))
    wrapper.findComponent(StoryBlock).vm.$emit('doAction', 'edge')
    await flushPromises()
    expect(wrapper.emitted('resynchronize')).toHaveLength(1)
    server.use(
      http.post(`${api}/story/do`, () =>
        HttpResponse.json({ detail: 'A permit is required.' }, { status: 400 })
      )
    )
    wrapper.findComponent(StoryBlock).vm.$emit('doAction', 'edge')
    await flushPromises()
    expect(wrapper.emitted('resynchronize')![1]).toEqual(['A permit is required.'])
  })

  it('ignores a response after its session is unmounted', async () => {
    const updated = vi.fn()
    let release!: () => void
    server.use(
      http.post(
        `${api}/story/do`,
        () =>
          new Promise((resolve) => {
            release = () => resolve(HttpResponse.json({ step: 2, fragments: [] }))
          })
      )
    )
    const wrapper = mount(StoryFlow, {
      props: { initialEnvelope: offered, activeChoiceIds: ['choice'], onStoryUpdate: updated },
      global: { plugins: [vuetify] },
    })
    await flushPromises()
    wrapper.findComponent(StoryBlock).vm.$emit('doAction', 'edge')
    await flushPromises()
    wrapper.unmount()
    release()
    await flushPromises()
    expect(updated).toHaveBeenCalledTimes(1)
  })

  it('submits a command through the existing typed find-edge request', async () => {
    const submitted: unknown[] = []
    server.use(
      http.post(`${api}/story/do`, async ({ request }) => {
        submitted.push(await request.json())
        return HttpResponse.json({ step: 2, fragments: [] })
      })
    )
    const wrapper = mountFlow(commandHintRuntimeEnvelope)
    await flushPromises()
    const input = wrapper.find('input')
    await input.setValue('look around')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(submitted).toEqual([{ find_edge: { kind: 'command', command: 'look around' } }])
  })
})
