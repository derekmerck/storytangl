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
  metadata?: Record<string, unknown>
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

  it('refreshes payload when the same choice uid receives new payload props', async () => {
    const choiceWithPayload: ChoiceStoryFragment = {
      uid: 'action_pb',
      fragment_type: 'choice',
      text: 'Choice',
      payload: { data: 'old' },
    }

    const wrapper = mountWithVuetify({ choice: choiceWithPayload })

    await wrapper.setProps({
      choice: {
        ...choiceWithPayload,
        payload: { data: 'new' },
      },
    })
    await wrapper.find('button').trigger('click')

    expect(wrapper.emitted('doAction')![0]).toEqual(['action_pb', { data: 'new' }])
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
    expect(wrapper.find('button').attributes('disabled')).toBeDefined()

    await wrapper.find('button').trigger('click')

    expect(wrapper.emitted('doAction')).toBeUndefined()
  })

  it('renders sandbox choice provenance and time hints as advisory badges', () => {
    const hintedChoice: ChoiceStoryFragment = {
      uid: 'wait_evening',
      fragment_type: 'choice',
      text: 'Wait until evening',
      ui_hints: {
        source_kind: 'schedule',
        contribution: 'time_advance',
        direction: 'wait',
        time_delta: { periods: 2, arrives_at: 'evening' },
      },
    }

    const wrapper = mountWithVuetify({ choice: hintedChoice })

    expect(wrapper.find('[data-testid="choice-hints"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('schedule')
    expect(wrapper.text()).toContain('time advance')
    expect(wrapper.text()).toContain('wait')
    expect(wrapper.text()).toContain('+2 periods')
    expect(wrapper.text()).toContain('arrives evening')
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

  it('renders structured piece accepts as piece options', () => {
    const pieceChoice: ChoiceStoryFragment = {
      uid: 'action_pieces',
      fragment_type: 'choice',
      text: 'Play a card',
      accepts: {
        kind: 'pieces',
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
        fragment_type: 'piece',
        piece_id: 'rust-map-card',
        content: 'Rust map card',
      },
    }

    const wrapper = mountWithVuetify({ choice: pieceChoice, fragments })

    expect(wrapper.find('[data-testid="choice-input-view"]').exists()).toBe(true)
    expect(wrapper.find('.choice-piece-option').exists()).toBe(true)
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

  it('emits raw command payloads through the reserved interpretation edge', async () => {
    const commandChoice: ChoiceStoryFragment = {
      uid: 'action_command',
      fragment_type: 'choice',
      edge_id: 'interpret_command',
      text: 'Try a command.',
      accepts: { kind: 'raw_command' },
    }

    const wrapper = mountWithVuetify({
      choice: commandChoice,
      metadata: {
        grammar: {
          examples: ['take lamp', 'open door'],
        },
      },
    })

    const input = wrapper.find('input')
    expect(input.attributes('placeholder')).toBe('e.g. take lamp')

    await input.setValue('take lamp')
    await wrapper.find('button').trigger('click')

    expect(wrapper.emitted('doAction')![0]).toEqual([
      'interpret_command',
      { text: 'take lamp' },
    ])
  })

  it('submits raw commands when grammar hints are missing or malformed', async () => {
    const commandChoice: ChoiceStoryFragment = {
      uid: 'action_command',
      fragment_type: 'choice',
      edge_id: 'interpret_command',
      text: 'Try a command.',
      accepts: { kind: 'raw_command' },
    }

    const wrapper = mountWithVuetify({
      choice: commandChoice,
      metadata: {
        grammar: {
          examples: [12, null],
          verbs: 'take',
        },
      },
    })

    const input = wrapper.find('input')
    expect(input.attributes('placeholder')).toBe('Type a command')

    await input.setValue('xyzzy')
    await input.trigger('keydown.enter')

    expect(wrapper.emitted('doAction')![0]).toEqual([
      'interpret_command',
      { text: 'xyzzy' },
    ])
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

  it('treats blank optional quantity accepts as empty rather than zero', async () => {
    const quantityChoice: ChoiceStoryFragment = {
      uid: 'action_quantity',
      fragment_type: 'choice',
      text: 'Buy optional rations',
      accepts: {
        kind: 'quantity',
        required: false,
        min: 1,
      },
    }

    const wrapper = mountWithVuetify({ choice: quantityChoice })

    await wrapper.find('button').trigger('click')

    expect(wrapper.emitted('doAction')![0]).toEqual(['action_quantity', undefined])
  })

  it('emits piece accepts payloads from visible target-zone pieces', async () => {
    const pieceChoice: ChoiceStoryFragment = {
      uid: 'action_pieces',
      fragment_type: 'choice',
      edge_id: 'edge_pieces',
      text: 'Take something',
      accepts: {
        kind: 'pieces',
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
        member_ids: ['lamp-fragment', 'sold-out-fragment'],
      },
      'lamp-fragment': {
        uid: 'lamp-fragment',
        fragment_type: 'piece',
        piece_id: 'lamp',
        content: 'brass lamp',
      },
      'sold-out-fragment': {
        uid: 'sold-out-fragment',
        fragment_type: 'piece',
        piece_id: 'sold-out',
        content: 'sold out offer',
        available: false,
        unavailable_reason: 'Out of stock',
      },
    }

    const wrapper = mountWithVuetify({ choice: pieceChoice, fragments })

    expect(wrapper.findAll('.choice-piece-option')).toHaveLength(1)
    expect(wrapper.text()).not.toContain('sold out offer')

    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('doAction')).toBeUndefined()

    await wrapper.find('.choice-piece-option').trigger('click')
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('doAction')![0]).toEqual([
      'edge_pieces',
      { piece_ids: ['lamp'] },
    ])
  })

  it('allows optional piece accepts with no selection', async () => {
    const pieceChoice: ChoiceStoryFragment = {
      uid: 'action_pieces_optional',
      fragment_type: 'choice',
      edge_id: 'edge_pieces_optional',
      text: 'Maybe take something',
      accepts: {
        kind: 'pieces',
        min: 0,
        constraints: { target_zone_ref: 'zone-room' },
      },
    }
    const fragments: Record<string, StoryFragment> = {
      'zone-room': {
        uid: 'zone-room',
        fragment_type: 'group',
        group_type: 'zone',
        member_ids: [],
      },
    }

    const wrapper = mountWithVuetify({ choice: pieceChoice, fragments })

    await wrapper.find('button').trigger('click')

    expect(wrapper.emitted('doAction')![0]).toEqual(['edge_pieces_optional', undefined])
  })

  it('marks multi-piece accepts as multi-select listboxes', () => {
    const pieceChoice: ChoiceStoryFragment = {
      uid: 'action_pieces_multi',
      fragment_type: 'choice',
      edge_id: 'edge_pieces_multi',
      text: 'Take some things',
      accepts: {
        kind: 'pieces',
        min: 0,
        max: 2,
        constraints: { target_zone_ref: 'zone-room' },
      },
    }
    const fragments: Record<string, StoryFragment> = {
      'zone-room': {
        uid: 'zone-room',
        fragment_type: 'group',
        group_type: 'zone',
        member_ids: ['lamp-fragment', 'coin-fragment'],
      },
      'lamp-fragment': {
        uid: 'lamp-fragment',
        fragment_type: 'piece',
        piece_id: 'lamp',
        content: 'brass lamp',
      },
      'coin-fragment': {
        uid: 'coin-fragment',
        fragment_type: 'piece',
        piece_id: 'coin',
        content: 'silver coin',
      },
    }

    const wrapper = mountWithVuetify({ choice: pieceChoice, fragments })

    expect(wrapper.find('.choice-piece-list').attributes('aria-multiselectable')).toBe('true')
  })

  it('emits place accepts payloads from visible source-zone pieces', async () => {
    const placeChoice: ChoiceStoryFragment = {
      uid: 'action_place',
      fragment_type: 'choice',
      edge_id: 'edge_place',
      text: 'Mount a weapon',
      accepts: {
        kind: 'place',
        source_zone_ref: 'zone-loose',
        target_zone_ref: 'zone-front',
        source_constraints: { target_kind: ['weapon'] },
      },
    }
    const fragments: Record<string, StoryFragment> = {
      'zone-loose': {
        uid: 'zone-loose',
        fragment_type: 'group',
        group_type: 'zone',
        zone_role: 'inventory',
        member_ids: ['flame-fragment'],
        hints: { label_text: 'parts on hand' },
      },
      'zone-front': {
        uid: 'zone-front',
        fragment_type: 'group',
        group_type: 'zone',
        zone_role: 'slot',
        member_ids: [],
        hints: { label_text: 'front mount' },
      },
      'flame-fragment': {
        uid: 'flame-fragment',
        fragment_type: 'piece',
        piece_id: 'flamethrower-1',
        content: 'Flamethrower',
      },
    }

    const wrapper = mountWithVuetify({ choice: placeChoice, fragments })

    expect(wrapper.find('[data-testid="choice-place-target"]').text()).toBe(
      'parts on hand to front mount',
    )
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('doAction')).toBeUndefined()

    await wrapper.find('.choice-piece-option').trigger('click')
    await wrapper.find('button').trigger('click')

    expect(wrapper.emitted('doAction')![0]).toEqual([
      'edge_place',
      {
        piece_id: 'flamethrower-1',
        source_zone_ref: 'zone-loose',
        target_zone_ref: 'zone-front',
      },
    ])
  })

  it('allows optional place accepts with no selection', async () => {
    const placeChoice: ChoiceStoryFragment = {
      uid: 'action_place_optional',
      fragment_type: 'choice',
      edge_id: 'edge_place_optional',
      text: 'Maybe mount a weapon',
      accepts: {
        kind: 'place',
        required: false,
        source_zone_ref: 'zone-loose',
        target_zone_ref: 'zone-front',
      },
    }
    const fragments: Record<string, StoryFragment> = {
      'zone-loose': {
        uid: 'zone-loose',
        fragment_type: 'group',
        group_type: 'zone',
        member_ids: [],
      },
      'zone-front': {
        uid: 'zone-front',
        fragment_type: 'group',
        group_type: 'zone',
        member_ids: [],
      },
    }

    const wrapper = mountWithVuetify({ choice: placeChoice, fragments })

    await wrapper.find('button').trigger('click')

    expect(wrapper.emitted('doAction')![0]).toEqual(['edge_place_optional', undefined])
  })

  it('clears stale piece payload when a same-uid choice points at a new zone', async () => {
    const pieceChoice: ChoiceStoryFragment = {
      uid: 'action_pieces',
      fragment_type: 'choice',
      edge_id: 'edge_pieces',
      text: 'Take something',
      accepts: {
        kind: 'pieces',
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
        fragment_type: 'piece',
        piece_id: 'lamp',
        content: 'brass lamp',
      },
    }

    const wrapper = mountWithVuetify({ choice: pieceChoice, fragments })

    await wrapper.find('.choice-piece-option').trigger('click')
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('doAction')![0]).toEqual([
      'edge_pieces',
      { piece_ids: ['lamp'] },
    ])

    await wrapper.setProps({
      choice: {
        ...pieceChoice,
        accepts: {
          kind: 'pieces',
          min: 1,
          max: 1,
          constraints: { target_zone_ref: 'zone-bag' },
        },
      },
      fragments: {
        'zone-bag': {
          uid: 'zone-bag',
          fragment_type: 'group',
          group_type: 'zone',
          member_ids: ['coin-fragment'],
        },
        'coin-fragment': {
          uid: 'coin-fragment',
          fragment_type: 'piece',
          piece_id: 'coin',
          content: 'silver coin',
        },
      },
    })
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('silver coin')
    expect(wrapper.text()).not.toContain('brass lamp')
    expect(wrapper.find('button').attributes('disabled')).toBeDefined()

    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('doAction')!.length).toBe(1)

    await wrapper.find('.choice-piece-option').trigger('click')
    await wrapper.find('button').trigger('click')
    const events = wrapper.emitted('doAction')!
    expect(events[events.length - 1]).toEqual([
      'edge_pieces',
      { piece_ids: ['coin'] },
    ])
  })

  it('preserves piece selection across same-zone fragment refreshes', async () => {
    const pieceChoice: ChoiceStoryFragment = {
      uid: 'action_pieces',
      fragment_type: 'choice',
      edge_id: 'edge_pieces',
      text: 'Take something',
      accepts: {
        kind: 'pieces',
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
        fragment_type: 'piece',
        piece_id: 'lamp',
        content: 'brass lamp',
      },
    }

    const wrapper = mountWithVuetify({ choice: pieceChoice, fragments })

    await wrapper.find('.choice-piece-option').trigger('click')
    await wrapper.setProps({
      fragments: {
        ...fragments,
        'lamp-fragment': {
          uid: 'lamp-fragment',
          fragment_type: 'piece',
          piece_id: 'lamp',
          content: 'polished brass lamp',
        },
      },
    })
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.choice-piece-option').classes()).toContain(
      'choice-piece-option--selected',
    )

    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('doAction')![0]).toEqual([
      'edge_pieces',
      { piece_ids: ['lamp'] },
    ])
  })
})
