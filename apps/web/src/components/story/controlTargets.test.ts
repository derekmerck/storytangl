import { describe, expect, it } from 'vitest'

import type { PresentationTarget, StoryFragment } from '@/types'
import { applyControlFragment, normalizeEnvelope } from './fragmentUtils'

const registry = (): Record<string, StoryFragment> => ({
  bob: {
    uid: 'bob',
    fragment_type: 'media',
    rit_id: 'portrait',
    media_role: 'avatar_im',
    presentation_handle: 'character:bob',
  },
  alice: {
    uid: 'alice',
    fragment_type: 'media',
    rit_id: 'portrait',
    media_role: 'avatar_im',
    presentation_handle: 'character:alice',
  },
  text: { uid: 'text', fragment_type: 'content', content: 'Hello' },
})

describe('explicit presentation targets', () => {
  it.each<[PresentationTarget, string[]]>([
    [{ kind: 'fragment', fragment_id: 'bob' }, ['alice', 'text']],
    [{ kind: 'rit', rit_id: 'portrait' }, ['text']],
    [{ kind: 'role', media_role: 'avatar_im' }, ['text']],
    [{ kind: 'handle', handle: 'character:bob' }, ['alice', 'text']],
    [{ kind: 'fragment', fragment_id: 'absent' }, ['bob', 'alice', 'text']],
    [{ kind: 'rit', rit_id: 'absent' }, ['bob', 'alice', 'text']],
    [{ kind: 'role', media_role: 'absent' }, ['bob', 'alice', 'text']],
    [{ kind: 'handle', handle: 'absent' }, ['bob', 'alice', 'text']],
  ])('deletes matching current uses for %o', (target, remaining) => {
    const state = registry()
    applyControlFragment(state, { uid: 'delete', fragment_type: 'delete', target })
    expect(Object.keys(state)).toEqual(remaining)
  })

  it('preserves ordinary content patches and does not upsert absent targets', () => {
    const state = registry()
    applyControlFragment(state, {
      uid: 'update',
      fragment_type: 'update',
      target: { kind: 'fragment', fragment_id: 'text' },
      payload: { content: 'Updated', uid: 'wrong' },
    })
    expect(state.text?.content).toBe('Updated')
    expect(state.text?.uid).toBe('text')
    applyControlFragment(state, {
      uid: 'update2',
      fragment_type: 'update',
      target: { kind: 'fragment', fragment_id: 'absent' },
      payload: { content: 'No upsert' },
    })
    expect(state.absent).toBeUndefined()
  })

  it('retains an explicit empty synchronization snapshot through normalization', () => {
    const envelope = normalizeEnvelope(
      { fragments: [], presentation: { music: null } },
      { fallbackPrefix: 'test' }
    )
    expect(envelope?.presentation).toEqual({ music: null })
  })
})
