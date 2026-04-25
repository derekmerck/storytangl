import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

import StoryAction from './StoryAction.vue'
import type { ChoiceStoryFragment } from '@/types'

const vuetify = createVuetify({ components, directives })

const mountWithVuetify = (props: { choice: ChoiceStoryFragment; disabled?: boolean }) =>
  mount(StoryAction, {
    props,
    global: {
      plugins: [vuetify],
    },
})

describe('StoryAction', () => {
  const mockChoice: ChoiceStoryFragment = {
    uid: 'action_123',
    fragment_type: 'choice',
    edge_id: 'edge_123',
    text: 'Make a choice',
  }

  it('renders choice text', () => {
    const wrapper = mountWithVuetify({ choice: mockChoice })
    expect(wrapper.text()).toContain('Make a choice')
  })

  it('emits doAction event with edge id when clicked', async () => {
    const wrapper = mountWithVuetify({ choice: mockChoice })

    await wrapper.find('button').trigger('click')

    expect(wrapper.emitted('doAction')).toBeTruthy()
    expect(wrapper.emitted('doAction')![0]).toEqual(['edge_123', undefined])
  })

  it('renders icon when provided', () => {
    const choiceWithIcon: ChoiceStoryFragment = {
      uid: 'action_icon',
      fragment_type: 'choice',
      text: 'Happy choice',
      ui_hints: { icon: 'emoticon-happy' },
    }

    const wrapper = mountWithVuetify({ choice: choiceWithIcon })

    expect(wrapper.find('.v-icon').exists()).toBe(true)
  })

  it('does not render icon when not provided', () => {
    const wrapper = mountWithVuetify({ choice: mockChoice })

    expect(wrapper.find('.v-icon').exists()).toBe(false)
  })

  it('emits doAction with payload when provided', async () => {
    const choiceWithPayload: ChoiceStoryFragment = {
      uid: 'action_pb',
      fragment_type: 'choice',
      text: 'Choice',
      payload: { data: 'value' },
    }

    const wrapper = mountWithVuetify({ choice: choiceWithPayload })

    await wrapper.find('button').trigger('click')

    expect(wrapper.emitted('doAction')![0]).toEqual(['action_pb', { data: 'value' }])
  })

  it('applies custom styles when provided', () => {
    const styledChoice: ChoiceStoryFragment = {
      uid: 'action_styled',
      fragment_type: 'choice',
      text: 'Styled',
      style: { color: 'red' },
    }

    const wrapper = mountWithVuetify({ choice: styledChoice })

    const button = wrapper.find('button')
    expect(button.attributes('style')).toContain('color')
  })

  it('renders locked choices with reason and does not emit', async () => {
    const lockedChoice: ChoiceStoryFragment = {
      uid: 'action_locked',
      fragment_type: 'choice',
      text: 'Sneak away',
      available: false,
      unavailable_reason: 'Requires stealth',
    }

    const wrapper = mountWithVuetify({ choice: lockedChoice })

    expect(wrapper.text()).toContain('Requires stealth')
    expect(wrapper.find('button').attributes('aria-disabled')).toBe('true')

    await wrapper.find('button').trigger('click')

    expect(wrapper.emitted('doAction')).toBeUndefined()
  })

  it('emits freeform payloads using accepts payload_type', async () => {
    const freeformChoice: ChoiceStoryFragment = {
      uid: 'action_freeform',
      fragment_type: 'choice',
      text: 'Haggle',
      accepts: {
        payload_type: 'offer_silver',
        input: 'integer',
        min: 1,
        max: 63,
      },
    }

    const wrapper = mountWithVuetify({ choice: freeformChoice })
    await wrapper.find('input').setValue('12')
    await wrapper.find('button').trigger('click')

    expect(wrapper.emitted('doAction')![0]).toEqual([
      'action_freeform',
      { offer_silver: 12 },
    ])
  })
})
