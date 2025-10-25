import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import App from '@/App.vue'
import StoryFlow from '@/components/story/StoryFlow.vue'

// Create Vuetify instance for testing
const vuetify = createVuetify({
  components,
  directives,
})

describe('App.vue', () => {
  it('renders the application shell', () => {
    const wrapper = mount(App, {
      global: {
        plugins: [vuetify],
      },
    })

    expect(wrapper.text()).toContain('WebTangl v3.7')
  })

  it('provides a container for the story flow', () => {
    const wrapper = mount(App, {
      global: {
        plugins: [vuetify],
      },
    })

    expect(wrapper.findComponent(StoryFlow).exists()).toBe(true)
  })

  it('wraps StoryFlow inside a Vuetify layout', () => {
    const wrapper = mount(App, {
      global: {
        plugins: [vuetify],
      },
    })

    const container = wrapper.find('.v-container')
    expect(container.exists()).toBe(true)
    expect(container.findComponent(StoryFlow).exists()).toBe(true)
  })
})
