import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

import StoryDialogBlock from './StoryDialogBlock.vue'
import type { DialogBlock } from '@/types'

const vuetify = createVuetify({ components, directives })

const mountComponent = (dialog_block: DialogBlock) =>
  mount(StoryDialogBlock, {
    props: { dialog_block },
    global: { plugins: [vuetify] },
  })

describe('StoryDialogBlock', () => {
  const basicDialog: DialogBlock = {
    uid: 'dialog-basic',
    text: 'Hello, traveler!',
  }

  it('renders dialog text', () => {
    const wrapper = mountComponent(basicDialog)
    expect(wrapper.text()).toContain('Hello, traveler!')
  })

  it('renders label when provided', () => {
    const labeledDialog: DialogBlock = {
      uid: 'dialog-labeled',
      text: 'I am the guardian.',
      label: 'Guardian',
    }

    const wrapper = mountComponent(labeledDialog)
    expect(wrapper.text()).toContain('Guardian')
    expect(wrapper.text()).toContain('I am the guardian.')
  })

  it('applies custom style when provided', () => {
    const styledDialog: DialogBlock = {
      uid: 'dialog-styled',
      text: 'Mysterious voice...',
      style: { color: 'purple', opacity: 0.8 },
    }

    const wrapper = mountComponent(styledDialog)
    const textElement = wrapper.find('[style]')
    expect(textElement.exists()).toBe(true)
    expect(textElement.attributes('style')).toContain('color')
  })

  it('renders avatar image when media_dict has avatar_im', () => {
    const dialogWithAvatar: DialogBlock = {
      uid: 'dialog-avatar',
      text: 'Nice to meet you!',
      label: 'Stranger',
      media_dict: {
        avatar_im: {
          media_role: 'avatar_im',
          url: 'https://example.com/avatar.jpg',
        },
      },
    }

    const wrapper = mountComponent(dialogWithAvatar)
    const avatar = wrapper.find('.v-avatar')
    expect(avatar.exists()).toBe(true)
    const img = avatar.find('img')
    expect(img.attributes('src')).toBe('https://example.com/avatar.jpg')
  })

  it('does not render avatar when no media provided', () => {
    const wrapper = mountComponent(basicDialog)
    expect(wrapper.find('.v-avatar').exists()).toBe(false)
  })

  it('handles dialog with no label but with avatar', () => {
    const dialog: DialogBlock = {
      uid: 'dialog-anon',
      text: 'Anonymous message',
      media_dict: {
        avatar_im: { media_role: 'avatar_im', url: 'https://example.com/anon.jpg' },
      },
    }

    const wrapper = mountComponent(dialog)
    expect(wrapper.find('.v-avatar').exists()).toBe(true)
    expect(wrapper.text()).not.toContain(':')
  })
})
