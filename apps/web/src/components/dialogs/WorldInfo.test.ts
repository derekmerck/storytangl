import { afterEach, beforeEach, describe, it, expect, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { setActivePinia, createPinia } from 'pinia'

import WorldInfo from './WorldInfo.vue'
import { useStore } from '@/store'

const vuetify = createVuetify({ components, directives })

const mountDialog = () =>
  mount(
    {
      components: { WorldInfo },
      template: '<v-app><WorldInfo model-value /></v-app>',
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

describe('WorldInfo', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
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

  it('renders dialog when modelValue is true', () => {
    const wrapper = mountDialog()
    const dialog = wrapper.findComponent(WorldInfo)
    expect(dialog.find('.v-dialog').exists()).toBe(true)
  })

  it('displays world title from store', async () => {
    const store = useStore()
    await store.getCurrentWorldInfo()

    const wrapper = mountDialog()
    await flushPromises()

    const dialog = wrapper.findComponent(WorldInfo)
    expect(dialog.text()).toContain('My world!')
  })

  it('displays world summary and version', async () => {
    const store = useStore()
    await store.getCurrentWorldInfo()

    const wrapper = mountDialog()
    await flushPromises()

    const dialog = wrapper.findComponent(WorldInfo)
    expect(dialog.text()).toContain('2.7.9')
    expect(dialog.text()).toContain('A cozy corner of the Tangl multiverse')
  })

  it('emits close when dialog is dismissed', async () => {
    const wrapper = mountDialog()
    const dialog = wrapper.findComponent(WorldInfo)
    const closeButton = dialog.findAll('button').find((btn) => btn.text().includes('Close'))
    await closeButton?.trigger('click')

    expect(dialog.emitted('update:modelValue')).toBeTruthy()
    expect(dialog.emitted('update:modelValue')?.[0]).toEqual([false])
  })
})
