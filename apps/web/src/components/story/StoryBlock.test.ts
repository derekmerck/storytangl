import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

import StoryBlock from './StoryBlock.vue'
import StoryAction from './StoryAction.vue'
import type { StoryFragment, StorySceneModel } from '@/types'

const vuetify = createVuetify({ components, directives })

const buildScene = (memberIds: string[]): StorySceneModel => ({
  key: 'scene-1',
  uid: 'scene-1',
  memberIds,
})

const mountBlock = (fragments: Record<string, StoryFragment>, memberIds: string[]) =>
  mount(StoryBlock, {
    props: {
      scene: buildScene(memberIds),
      fragments,
    },
    global: {
      plugins: [vuetify],
      components: {
        StoryAction,
      },
    },
  })

describe('StoryBlock', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_DEBUG', 'false')
    vi.stubEnv('VITE_VERBOSE', 'false')
  })

  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it('renders content fragments', () => {
    const fragments: Record<string, StoryFragment> = {
      content: {
        uid: 'content',
        fragment_type: 'content',
        content: 'You enter a dark room.',
      },
    }

    const wrapper = mountBlock(fragments, ['content'])

    expect(wrapper.text()).toContain('You enter a dark room.')
  })

  it('escapes HTML content in content fragments', () => {
    const fragments: Record<string, StoryFragment> = {
      content: {
        uid: 'content',
        fragment_type: 'content',
        content: '<p>Paragraph with <strong>bold</strong> text</p>',
        content_format: 'html',
      },
    }

    const wrapper = mountBlock(fragments, ['content'])

    expect(wrapper.text()).toContain('<p>Paragraph with <strong>bold</strong> text</p>')
    expect(wrapper.html()).not.toContain('<strong>bold</strong>')
  })

  it('renders media fragments using canonical content URLs', () => {
    const fragments: Record<string, StoryFragment> = {
      media: {
        uid: 'media',
        fragment_type: 'media',
        content: 'https://example.com/portrait.svg',
        content_format: 'url',
        media_role: 'narrative_im',
        staging_hints: { media_shape: 'portrait' },
      },
    }

    const wrapper = mountBlock(fragments, ['media'])
    const img = wrapper.findComponent({ name: 'VImg' })

    expect(img.exists()).toBe(true)
    expect(img.props('src')).toBe('https://example.com/portrait.svg')
  })

  it('renders pending RIT media placeholders', () => {
    const fragments: Record<string, StoryFragment> = {
      media: {
        uid: 'media',
        fragment_type: 'media',
        content: 'gen:portrait',
        content_format: 'rit',
        media_role: 'dialog_im',
      },
    }

    const wrapper = mountBlock(fragments, ['media'])

    expect(wrapper.find('[data-testid="pending-media"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('gen:portrait')
  })

  it('renders dialog groups from attributed and media fragments', () => {
    const fragments: Record<string, StoryFragment> = {
      dialog: {
        uid: 'dialog',
        fragment_type: 'group',
        group_type: 'dialog',
        member_ids: ['line', 'avatar'],
      },
      line: {
        uid: 'line',
        fragment_type: 'attributed',
        who: 'Guard',
        how: 'stern',
        media: 'speech',
        content: 'Who goes there?',
      },
      avatar: {
        uid: 'avatar',
        fragment_type: 'media',
        content: 'https://example.com/avatar.svg',
        content_format: 'url',
        media_role: 'avatar_im',
      },
    }

    const wrapper = mountBlock(fragments, ['dialog'])

    expect(wrapper.text()).toContain('Guard')
    expect(wrapper.text()).toContain('Who goes there?')
    expect(wrapper.find('.v-avatar').exists()).toBe(true)
  })

  it('renders kv fragments as scene status', () => {
    const fragments: Record<string, StoryFragment> = {
      kv: {
        uid: 'kv',
        fragment_type: 'kv',
        content: [
          ['time', 'late'],
          ['coin', 63],
        ],
      },
    }

    const wrapper = mountBlock(fragments, ['kv'])

    expect(wrapper.text()).toContain('time')
    expect(wrapper.text()).toContain('63')
  })

  it('renders zone groups with token labels and state', () => {
    const fragments: Record<string, StoryFragment> = {
      zone: {
        uid: 'zone',
        fragment_type: 'group',
        group_type: 'zone',
        zone_role: 'player_hand',
        member_ids: ['token'],
        hints: { label_text: 'Traveler hand' },
      },
      token: {
        uid: 'token',
        fragment_type: 'token',
        token_id: 'rust-map-card',
        content: 'Rust map card',
        display_state: 'face_up',
      },
    }

    const wrapper = mountBlock(fragments, ['zone'])

    expect(wrapper.find('[data-testid="zone-fragment"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="token-fragment"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Traveler hand')
    expect(wrapper.text()).toContain('Rust map card')
    expect(wrapper.text()).toContain('face up')
  })

  it('renders empty zones without falling back to unknown group text', () => {
    const fragments: Record<string, StoryFragment> = {
      zone: {
        uid: 'zone',
        fragment_type: 'group',
        group_type: 'zone',
        zone_role: 'discard',
        member_ids: [],
      },
    }

    const wrapper = mountBlock(fragments, ['zone'])

    expect(wrapper.find('[data-testid="zone-fragment"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="empty-zone"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('discard')
    expect(wrapper.text()).toContain('Empty')
    expect(wrapper.find('[data-testid="fragment-fallback"]').exists()).toBe(false)
  })

  it('keeps fallback rendering for unsupported zone members', () => {
    const fragments: Record<string, StoryFragment> = {
      zone: {
        uid: 'zone',
        fragment_type: 'group',
        group_type: 'zone',
        member_ids: ['clock'],
        hints: { label_text: 'Countdown' },
      },
      clock: {
        uid: 'clock',
        fragment_type: 'clock',
        content: 'three ticks',
      },
    }

    const wrapper = mountBlock(fragments, ['zone'])

    expect(wrapper.find('[data-testid="zone-fragment"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="fragment-fallback"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Countdown')
    expect(wrapper.text()).toContain('clock')
    expect(wrapper.text()).toContain('three ticks')
  })

  it('renders standalone token fragments', () => {
    const fragments: Record<string, StoryFragment> = {
      token: {
        uid: 'token',
        fragment_type: 'token',
        token_id: 'lantern-token',
        kind: 'tool',
        label: 'Brass lantern',
        display_state: 'ready',
      },
    }

    const wrapper = mountBlock(fragments, ['token'])

    expect(wrapper.find('[data-testid="token-fragment"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Brass lantern')
    expect(wrapper.text()).toContain('ready')
  })

  it('renders choices and emits selected edge ids', async () => {
    const fragments: Record<string, StoryFragment> = {
      content: {
        uid: 'content',
        fragment_type: 'content',
        content: 'Choose:',
      },
      choice: {
        uid: 'choice',
        fragment_type: 'choice',
        edge_id: 'edge-1',
        text: 'Continue',
      },
    }

    const wrapper = mountBlock(fragments, ['content', 'choice'])
    const action = wrapper.findComponent(StoryAction)
    await action.vm.$emit('doAction', 'edge-1', undefined)

    expect(wrapper.text()).toContain('Continue')
    expect(wrapper.emitted('doAction')![0]).toEqual(['edge-1', undefined])
  })

  it('renders unknown fragments as fallbacks', () => {
    const fragments: Record<string, StoryFragment> = {
      weird: {
        uid: 'weird',
        fragment_type: 'dice_roll',
        content: { value: 6 },
      },
    }

    const wrapper = mountBlock(fragments, ['weird'])

    expect(wrapper.find('[data-testid="fragment-fallback"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('dice_roll')
  })
})
