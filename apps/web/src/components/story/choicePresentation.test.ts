import { describe, expect, it } from 'vitest'

import type { ChoiceStoryFragment } from '@/types'
import {
  CHOICE_KEYS,
  choiceKeyForPosition,
  choiceKeysForList,
  choicePresentation,
} from './choicePresentation'

const choice = (overrides: Partial<ChoiceStoryFragment> = {}): ChoiceStoryFragment => ({
  uid: 'choice',
  fragment_type: 'choice',
  edge_id: 'edge',
  text: 'Choose',
  ...overrides,
})

describe('choice presentation', () => {
  it('uses the shared positional alphabet and prints no unaccepted key', () => {
    expect(choiceKeyForPosition(choice(), 9)).toBe('9')
    expect(choiceKeyForPosition(choice(), 10)).toBe('a')
    expect(CHOICE_KEYS).not.toContain('x')
    expect(choiceKeyForPosition(choice(), CHOICE_KEYS.length + 1)).toBeUndefined()
  })

  it('honours authored hotkeys only for available choices', () => {
    expect(choiceKeyForPosition(choice({ ui_hints: { hotkey: 'q' } }), 1)).toBe('q')
    expect(
      choiceKeyForPosition(choice({ available: false, ui_hints: { hotkey: 'q' } }), 1)
    ).toBeUndefined()
    expect(
      choiceKeysForList([
        choice({ available: false, ui_hints: { hotkey: 'q' } }),
        choice({ edge_id: 'edge-live', ui_hints: { hotkey: 'q' } }),
      ])
    ).toEqual([undefined, 'q'])
  })

  it('rejects duplicate resolved hotkeys after web keyboard normalization', () => {
    expect(() =>
      choiceKeysForList([
        choice({ edge_id: 'edge-first', ui_hints: { hotkey: 'Q' } }),
        choice({ edge_id: 'edge-second', ui_hints: { hotkey: 'q' } }),
      ])
    ).toThrow(
      'Duplicate choice hotkey "q" for positions 1 (edge-first) and 2 (edge-second)'
    )
  })

  it('lets a later replacement blocker become the row exactly once', () => {
    const presented = choicePresentation(
      choice({
        text: 'Trade the paperclip',
        available: false,
        unavailable_reason: 'not_holding',
        blockers: [
          { code: 'closed', message: 'The stall is shut.' },
          {
            code: 'not_holding',
            message: 'Mira would trade, but you do not have the doorknob.',
            replaces_text: true,
          },
        ],
      })
    )

    expect(presented).toEqual({
      text: 'Mira would trade, but you do not have the doorknob.',
      refusal: undefined,
      refusalRefs: [],
      refusalFromBlocker: false,
    })
  })
})
