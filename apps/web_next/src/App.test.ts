import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import App from '@/App.vue'

// Create Vuetify instance for testing
const vuetify = createVuetify({
  components,
  directives,
})

describe('App.vue', () => {
  it('renders hello message', () => {
    const wrapper = mount(App, {
      global: {
        plugins: [vuetify],
      },
    })

    expect(wrapper.text()).toContain('Hello StoryTangl!')
  })

  it('increments counter when button is clicked', async () => {
    const wrapper = mount(App, {
      global: {
        plugins: [vuetify],
      },
    })

    const button = wrapper.find('button')
    expect(wrapper.text()).toContain('Counter: 0')

    await button.trigger('click')
    expect(wrapper.text()).toContain('Counter: 1')

    await button.trigger('click')
    expect(wrapper.text()).toContain('Counter: 2')
  })

  it('displays success alert', () => {
    const wrapper = mount(App, {
      global: {
        plugins: [vuetify],
      },
    })

    expect(wrapper.text()).toContain('Vue 3, Vuetify 3, TypeScript, and Vite are all configured!')
  })
})
