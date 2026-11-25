import { afterEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'

import StageView from './StageView.vue'
import { reparteeSteps } from '@tests/fixtures'
import type { MediaStoryFragment } from '@/types'

const quay = reparteeSteps[1]!.fragments[1] as MediaStoryFragment

/** Report one frame width to every observer, as the browser does on layout. */
const observeFrameWidth = (width: number) => {
  const observers: ResizeObserverCallback[] = []
  vi.stubGlobal(
    'ResizeObserver',
    class {
      constructor(callback: ResizeObserverCallback) {
        observers.push(callback)
      }
      observe() {
        observers.forEach((callback) =>
          callback([{ contentRect: { width } } as ResizeObserverEntry], this as never)
        )
      }
      disconnect() {}
    }
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('StageView', () => {
  it('rescales the canvas when the world declares its extent after mounting', async () => {
    observeFrameWidth(640)
    const wrapper = mount(StageView, {
      props: { images: [quay], extent: { width: 320, height: 200 } },
    })
    await nextTick()
    const canvas = () => wrapper.find('.stage-canvas').attributes('style')
    expect(canvas()).toContain('scale(2)')

    // World info arrives late; the frame keeps its width, so no resize fires.
    await wrapper.setProps({ extent: { width: 640, height: 400 } })
    expect(canvas()).toContain('width: 640px')
    expect(canvas()).toContain('scale(1)')
  })

  it('keeps a figure restated in a later step as the same element', async () => {
    const clerk = { ...(reparteeSteps[1]!.fragments[2] as MediaStoryFragment), rit_id: 'clerk-rit' }
    const wrapper = mount(StageView, {
      props: { images: [quay, { ...clerk, uid: 'court-clerk' }], extent: { width: 320, height: 200 } },
    })
    const figure = () => wrapper.find('img[data-stage-role="dialog_im"]').element

    // A later step restates the room: new fragment uids, the same resources.
    const first = figure()
    await wrapper.setProps({ images: [{ ...quay, uid: 'later-bg' }, { ...clerk, uid: 'later-clerk' }] })
    expect(figure()).toBe(first)
  })

  it('numbers repeats of one resource so each is its own figure', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const figure = reparteeSteps[1]!.fragments[2] as MediaStoryFragment
    const crowd = { ...figure, rit_id: 'extra' }
    const other = { ...figure, rit_id: 'other', uid: 'other' }
    const wrapper = mount(StageView, {
      props: { images: [quay, other, { ...crowd, uid: 'a' }], extent: { width: 320, height: 200 } },
    })
    // A later step restates the room with two figures drawn from one resource.
    await wrapper.setProps({
      images: [quay, { ...crowd, uid: 'b' }, { ...crowd, uid: 'c' }, { ...other, uid: 'd' }],
    })

    expect(wrapper.findAll('img[data-stage-role="dialog_im"]')).toHaveLength(3)
    expect(warn.mock.calls.map(([message]) => String(message))).not.toContainEqual(
      expect.stringContaining('Duplicate keys')
    )
    warn.mockRestore()
  })
})
