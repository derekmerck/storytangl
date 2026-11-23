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
})
