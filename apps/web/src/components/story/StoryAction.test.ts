import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

import StoryAction from './StoryAction.vue'
import type { ChoiceStoryFragment, StoryFragment } from '@/types'

const vuetify = createVuetify({ components, directives })

const mountWithVuetify = (props: {
  choice: ChoiceStoryFragment
  fragments?: Record<string, StoryFragment>
  disabled?: boolean
}) =>
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

  it('renders structured token accepts as token options', () => {
    const tokenChoice: ChoiceStoryFragment = {
      uid: 'action_tokens',
      fragment_type: 'choice',
      text: 'Play a card',
      accepts: {
        kind: 'tokens',
        min: 1,
        max: 1,
        constraints: { target_zone_ref: 'zone-hand' },
      },
    }
    const fragments: Record<string, StoryFragment> = {
      'zone-hand': {
        uid: 'zone-hand',
        fragment_type: 'group',
        group_type: 'zone',
        member_ids: ['card'],
      },
      card: {
        uid: 'card',
        fragment_type: 'token',
        token_id: 'rust-map-card',
        content: 'Rust map card',
      },
    }

    const wrapper = mountWithVuetify({ choice: tokenChoice, fragments })

    expect(wrapper.find('[data-testid="choice-input-view"]').exists()).toBe(true)
    expect(wrapper.find('.choice-token-option').exists()).toBe(true)
    expect(wrapper.text()).toContain('Rust map card')
  })

  it('does not emit blank or out-of-range numeric freeform payloads', async () => {
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

    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('doAction')).toBeUndefined()

    await wrapper.find('input').setValue('0')
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('doAction')).toBeUndefined()

    await wrapper.find('input').setValue('64')
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('doAction')).toBeUndefined()
  })

  it('emits text accepts payloads after validation passes', async () => {
    const textChoice: ChoiceStoryFragment = {
      uid: 'action_text',
      fragment_type: 'choice',
      text: 'Name your sword',
      accepts: {
        kind: 'text',
        validators: [{ kind: 'length', min: 2, max: 12 }],
      },
    }

    const wrapper = mountWithVuetify({ choice: textChoice })

    await wrapper.find('input').setValue('A')
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('doAction')).toBeUndefined()

    await wrapper.find('input').setValue('Hope')
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('doAction')![0]).toEqual(['action_text', { text: 'Hope' }])
  })

  it('emits quantity accepts payloads after min/max validation passes', async () => {
    const quantityChoice: ChoiceStoryFragment = {
      uid: 'action_quantity',
      fragment_type: 'choice',
      text: 'Buy rations',
      accepts: {
        kind: 'quantity',
        min: 1,
        max: 3,
        unit: 'ration',
      },
    }

    const wrapper = mountWithVuetify({ choice: quantityChoice })

    await wrapper.find('input').setValue('0')
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('doAction')).toBeUndefined()

    await wrapper.find('input').setValue('2')
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('doAction')![0]).toEqual([
      'action_quantity',
      { quantity: 2 },
    ])
  })

  it('emits token accepts payloads from visible target-zone tokens', async () => {
    const tokenChoice: ChoiceStoryFragment = {
      uid: 'action_tokens',
      fragment_type: 'choice',
      edge_id: 'edge_tokens',
      text: 'Take something',
      accepts: {
        kind: 'tokens',
        min: 1,
        max: 1,
        constraints: { target_zone_ref: 'zone-room' },
      },
    }
    const fragments: Record<string, StoryFragment> = {
      'zone-room': {
        uid: 'zone-room',
        fragment_type: 'group',
        group_type: 'zone',
        member_ids: ['lamp-fragment'],
      },
      'lamp-fragment': {
        uid: 'lamp-fragment',
        fragment_type: 'token',
        token_id: 'lamp',
        content: 'brass lamp',
      },
    }

    const wrapper = mountWithVuetify({ choice: tokenChoice, fragments })

    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('doAction')).toBeUndefined()

    await wrapper.find('.choice-token-option').trigger('click')
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('doAction')![0]).toEqual([
      'edge_tokens',
      { token_ids: ['lamp'] },
    ])
  })
})
