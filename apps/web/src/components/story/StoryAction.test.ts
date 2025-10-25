import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

import StoryAction from './StoryAction.vue'
import type { JournalAction } from '@/types'

const vuetify = createVuetify({ components, directives })

const mountWithVuetify = (props: { action: JournalAction }) =>
  mount(StoryAction, {
    props,
    global: {
      plugins: [vuetify],
    },
  })

describe('StoryAction', () => {
  const mockAction: JournalAction = {
    uid: 'action_123',
    text: 'Make a choice',
  }

  it('renders action text', () => {
    const wrapper = mountWithVuetify({ action: mockAction })
    expect(wrapper.text()).toContain('Make a choice')
  })

  it('emits doAction event with uid when clicked', async () => {
    const wrapper = mountWithVuetify({ action: mockAction })

    await wrapper.find('button').trigger('click')

    expect(wrapper.emitted('doAction')).toBeTruthy()
    expect(wrapper.emitted('doAction')![0]).toEqual(['action_123', undefined])
  })

  it('renders icon when provided', () => {
    const actionWithIcon: JournalAction = {
      uid: 'action_icon',
      text: 'Happy choice',
      icon: 'emoticon-happy',
    }

    const wrapper = mountWithVuetify({ action: actionWithIcon })

    expect(wrapper.find('.v-icon').exists()).toBe(true)
  })

  it('does not render icon when not provided', () => {
    const wrapper = mountWithVuetify({ action: mockAction })

    expect(wrapper.find('.v-icon').exists()).toBe(false)
  })

  it('emits doAction with passback when provided', async () => {
    const actionWithPassback: JournalAction = {
      uid: 'action_pb',
      text: 'Choice',
      passback: { data: 'value' },
    }

    const wrapper = mountWithVuetify({ action: actionWithPassback })

    await wrapper.find('button').trigger('click')

    expect(wrapper.emitted('doAction')![0]).toEqual(['action_pb', { data: 'value' }])
  })

  it('applies custom styles when provided', () => {
    const styledAction: JournalAction = {
      uid: 'action_styled',
      text: 'Styled',
      style: { color: 'red' },
    }

    const wrapper = mountWithVuetify({ action: styledAction })

    const button = wrapper.find('button')
    expect(button.attributes('style')).toContain('color')
  })
})
