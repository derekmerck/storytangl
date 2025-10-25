import { afterEach, beforeEach, describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { setActivePinia, createPinia } from 'pinia'

import SecretDialog from './SecretDialog.vue'
import { useStore } from '@/store'

const vuetify = createVuetify({ components, directives })

const mountDialog = (modelValue = true) =>
  mount(
    {
      components: { SecretDialog },
      props: {
        modelValue: {
          type: Boolean,
          default: true,
        },
      },
      template: '<v-app><SecretDialog :model-value="modelValue" /></v-app>',
    },
    {
      props: { modelValue },
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
      attachTo: document.body,
    },
  )

describe('SecretDialog', () => {
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
    // Clean up between tests to avoid cross-test pollution
    delete (globalThis as { visualViewport?: unknown }).visualViewport
    document.body.innerHTML = ''
  })

  it('renders dialog when modelValue is true', async () => {
    const wrapper = mountDialog(true)
    await flushPromises()
    await nextTick()
    const dialog = wrapper.findComponent(SecretDialog)
    expect(dialog.find('.v-dialog').exists()).toBe(true)
  })

  it('does not render dialog when modelValue is false', async () => {
    const wrapper = mountDialog(false)
    await flushPromises()
    await nextTick()
    const dialog = wrapper.findComponent(SecretDialog)
    expect(dialog.find('.v-dialog').exists()).toBe(false)
  })

  it('has text field for user secret', async () => {
    const wrapper = mountDialog(true)
    await flushPromises()
    await nextTick()
    const textField = wrapper.findComponent(SecretDialog).find('input[type="text"]')
    expect(textField.exists()).toBe(true)
  })

  it('has save and cancel buttons', async () => {
    const wrapper = mountDialog(true)
    await flushPromises()
    await nextTick()
    const buttons = wrapper.findComponent(SecretDialog).findAll('button')
    expect(buttons.some((btn) => btn.text().includes('Save'))).toBe(true)
    expect(buttons.some((btn) => btn.text().includes('Cancel'))).toBe(true)
  })

  it('emits update:modelValue false when cancel clicked', async () => {
    const wrapper = mountDialog(true)
    await flushPromises()
    await nextTick()
    const dialog = wrapper.findComponent(SecretDialog)
    const cancelButton = dialog
      .findAll('button')
      .find((button) => button.text().includes('Cancel'))
    await cancelButton?.trigger('click')

    expect(dialog.emitted('update:modelValue')).toBeTruthy()
    expect(dialog.emitted('update:modelValue')?.[0]).toEqual([false])
  })

  it('calls store.setApiKey when save clicked', async () => {
    const wrapper = mountDialog(true)
    await flushPromises()
    await nextTick()
    const dialog = wrapper.findComponent(SecretDialog)
    const input = dialog.find('input[type="text"]')
    await input.setValue('new-secret')

    const saveButton = dialog
      .findAll('button')
      .find((button) => button.text().includes('Save'))

    await saveButton?.trigger('click')
    await flushPromises()

    const store = useStore()
    expect(store.user_secret).toBe('new-secret')
    expect(dialog.emitted('update:modelValue')).toBeTruthy()
  })
})
