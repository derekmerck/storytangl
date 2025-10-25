import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

import AppFooter from './AppFooter.vue'

const vuetify = createVuetify({ components, directives })

describe('AppFooter', () => {
  const mountFooter = () =>
    mount(AppFooter, {
      global: {
        plugins: [vuetify],
        stubs: {
          'v-footer': { template: '<footer class="v-footer"><slot /></footer>' },
          'v-row': { template: '<div class="v-row"><slot /></div>' },
          'v-col': { template: '<div class="v-col"><slot /></div>' },
        },
      },
    })

  it('renders footer container', () => {
    const wrapper = mountFooter()

    expect(wrapper.find('.v-footer').exists()).toBe(true)
  })

  it('displays version and year', () => {
    const wrapper = mountFooter()

    expect(wrapper.text()).toContain('WebTangl v3.7.0')
    expect(wrapper.text()).toContain(new Date().getFullYear().toString())
  })
})
