import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

import StoryBlock from './StoryBlock.vue'
import StoryAction from './StoryAction.vue'
import StoryDialogBlock from './StoryDialogBlock.vue'
import type { JournalStoryUpdate } from '@/types'

const vuetify = createVuetify({ components, directives })

const mountBlock = (block: JournalStoryUpdate) =>
  mount(StoryBlock, {
    props: { block },
    global: {
      plugins: [vuetify],
      components: {
        StoryAction,
        StoryDialogBlock,
      },
    },
  })

describe('StoryBlock', () => {
  let simpleBlock: JournalStoryUpdate

  beforeEach(() => {
    // Ensure tests run in non-verbose mode, otherwise 'notContains'
    // will pick up debug info
    vi.stubEnv('VITE_DEBUG', 'false')
    vi.stubEnv('VITE_VERBOSE', 'false')
    simpleBlock = {
      uid: 'block_1',
      text: 'You enter a dark room.',
    }
  })

  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it('renders block text', () => {
    const wrapper = mountBlock(simpleBlock)
    expect(wrapper.text()).toContain('You enter a dark room.')
  })

  it('renders title when provided', () => {
    const blockWithTitle: JournalStoryUpdate = {
      uid: 'block_2',
      title: 'Chapter 1',
      text: 'The story begins...',
    }

    const wrapper = mountBlock(blockWithTitle)
    expect(wrapper.text()).toContain('Chapter 1')
    expect(wrapper.text()).toContain('The story begins...')
  })

  it('renders HTML in text field', () => {
    const blockWithHTML: JournalStoryUpdate = {
      uid: 'block_3',
      text: '<p>Paragraph with <strong>bold</strong> text</p>',
    }

    const wrapper = mountBlock(blockWithHTML)
    expect(wrapper.html()).toContain('<strong>bold</strong>')
  })

  it('renders landscape image when orientation is landscape', () => {
    const blockWithLandscape: JournalStoryUpdate = {
      uid: 'block_4',
      text: 'A vast landscape...',
      media_dict: {
        narrative_im: {
          media_role: 'narrative_im',
          url: 'https://example.com/landscape.jpg',
          orientation: 'landscape',
        },
      },
    }

    const wrapper = mountBlock(blockWithLandscape)
    expect(wrapper.find('.v-parallax').exists()).toBe(true)
  })

  it('renders portrait image inline when orientation is portrait', () => {
    const blockWithPortrait: JournalStoryUpdate = {
      uid: 'block_5',
      text: 'A tall tower...',
      media_dict: {
        narrative_im: {
          media_role: 'narrative_im',
          url: 'https://example.com/portrait.jpg',
          orientation: 'portrait',
        },
      },
    }

    const wrapper = mountBlock(blockWithPortrait)
    const img = wrapper.findComponent({ name: 'VImg' })
    expect(img.exists()).toBe(true)
    expect(img.props('src')).toBe('https://example.com/portrait.jpg')
  })

  it('renders square image inline when orientation is square', () => {
    const blockWithSquare: JournalStoryUpdate = {
      uid: 'block_6',
      text: 'An artifact...',
      media_dict: {
        narrative_im: {
          media_role: 'narrative_im',
          url: 'https://example.com/square.jpg',
          orientation: 'square',
        },
      },
    }

    const wrapper = mountBlock(blockWithSquare)
    const img = wrapper.findComponent({ name: 'VImg' })
    expect(img.exists()).toBe(true)
  })

  it('renders dialog blocks when present', () => {
    const blockWithDialog: JournalStoryUpdate = {
      uid: 'block_7',
      dialog: [
        { uid: 'dialog-1', text: 'Hello!', label: 'Guard' },
        { uid: 'dialog-2', text: 'Who goes there?', label: 'Guard' },
      ],
    }

    const wrapper = mountBlock(blockWithDialog)
    const dialogs = wrapper.findAllComponents(StoryDialogBlock)
    expect(dialogs).toHaveLength(2)
  })

  it('renders text when no dialog present', () => {
    const wrapper = mountBlock(simpleBlock)
    const cardText = wrapper.find('.v-card-text')
    expect(cardText.exists()).toBe(true)
    expect(cardText.html()).toContain('You enter a dark room.')
  })

  it('does not render text when dialog is present', () => {
    const blockWithDialog: JournalStoryUpdate = {
      uid: 'block_8',
      text: 'This should not appear',
      dialog: [{ uid: 'dialog-3', text: 'Dialog takes precedence' }],
    }

    const wrapper = mountBlock(blockWithDialog)
    expect(wrapper.text()).not.toContain('This should not appear')
  })

  it('renders actions when provided', () => {
    const blockWithActions: JournalStoryUpdate = {
      uid: 'block_9',
      text: 'What do you do?',
      actions: [
        { uid: 'action_1', text: 'Go north' },
        { uid: 'action_2', text: 'Go south' },
      ],
    }

    const wrapper = mountBlock(blockWithActions)
    const actions = wrapper.findAllComponents(StoryAction)
    expect(actions).toHaveLength(2)
  })

  it('emits doAction when action is clicked', async () => {
    const blockWithActions: JournalStoryUpdate = {
      uid: 'block_10',
      text: 'Choose:',
      actions: [{ uid: 'action_1', text: 'Choice 1' }],
    }

    const wrapper = mountBlock(blockWithActions)
    const action = wrapper.findComponent(StoryAction)
    await action.vm.$emit('doAction', 'action_1', null)

    const emissions = wrapper.emitted('doAction')
    expect(emissions).toBeTruthy()
    const [blockArg, uidArg, passbackArg] = emissions![0] as [
      JournalStoryUpdate,
      string,
      unknown,
    ]
    expect(blockArg).toEqual(blockWithActions)
    expect(uidArg).toBe('action_1')
    expect(passbackArg).toBeNull()
  })
})
