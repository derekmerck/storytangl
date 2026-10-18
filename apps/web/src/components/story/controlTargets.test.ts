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

const initialStaging = {
  media_x: 0.1,
  media_y: 0.8,
  media_size: 0.5,
  media_clip: 'idle',
  media_timing: 'loop',
  media_visibility: { preference_id: 'sprites', values: [true] },
}

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
      { fallbackPrefix: 'test' },
    )
    expect(envelope?.presentation).toEqual({ music: null })
  })

  it('moves and captions a handle without resupplying or changing its resource', () => {
    const state = registry()
    applyControlFragment(state, {
      uid: 'move',
      fragment_type: 'update',
      target: { kind: 'handle', handle: 'character:bob' },
      patch_kind: 'presentation',
      payload: {
        text: 'Bob speaks',
        staging_hints: {
          media_x: 0.25,
          media_visibility: { preference_id: 'shown', values: [true] },
        },
      },
    })
    expect(state.bob).toMatchObject({
      uid: 'bob',
      rit_id: 'portrait',
      text: 'Bob speaks',
      staging_hints: {
        media_x: 0.25,
        media_visibility: { preference_id: 'shown', values: [true] },
      },
    })
    expect(state.alice).not.toHaveProperty('text')
    applyControlFragment(state, {
      uid: 'not-a-media-edit',
      fragment_type: 'update',
      target: { kind: 'fragment', fragment_id: 'bob' },
      payload: { content: { url: 'https://example.invalid/wrong' }, data: 'wrong' },
    })
    expect(state.bob).not.toHaveProperty('content')
    expect(state.bob).not.toHaveProperty('data')
  })

  it('replaces matched media completely, preserving the addressed uid and not upserting', () => {
    const state = registry()
    state.bob = { ...state.bob!, fragment_type: 'media', url: '/old', data: 'old' }
    const replacement = {
      uid: 'resource-descriptor',
      fragment_type: 'media' as const,
      rit_id: 'new-resource',
      content_format: 'url',
      url: '/new',
      media_role: 'avatar_im',
    }
    for (const fragment_id of ['bob', 'text', 'absent']) {
      applyControlFragment(state, {
        uid: 'replace',
        fragment_type: 'update',
        target: { kind: 'fragment', fragment_id },
        media: replacement,
      })
    }
    expect(state.bob).toEqual({ ...replacement, uid: 'bob' })
    expect(state.text?.fragment_type).toBe('content')
    expect(state.absent).toBeUndefined()
  })

  it('retains loop across same-resource replacement and presentation updates', () => {
    const state: Record<string, StoryFragment> = {
      music: {
        uid: 'music',
        fragment_type: 'media',
        rit_id: 'a',
        media_role: 'music',
        staging_hints: initialStaging,
      },
    }
    applyControlFragment(state, {
      uid: 'replace',
      fragment_type: 'update',
      target: { kind: 'role', media_role: 'music' },
      media: { uid: 'descriptor', fragment_type: 'media', rit_id: 'a', media_role: 'music' },
    })
    expect(state.music?.staging_hints).toEqual({ media_timing: 'loop' })
    applyControlFragment(state, {
      uid: 'caption',
      fragment_type: 'update',
      target: { kind: 'role', media_role: 'music' },
      patch_kind: 'presentation',
      payload: { text: 'A caption', staging_hints: { media_x: 0.5 } },
    })
    expect(state.music).toMatchObject({
      uid: 'music',
      staging_hints: { media_timing: 'loop', media_x: 0.5 },
    })
    applyControlFragment(state, {
      uid: 'stop',
      fragment_type: 'delete',
      target: { kind: 'role', media_role: 'music' },
    })
    expect(state).toEqual({})
  })

  it.each<[Record<string, unknown>, Record<string, unknown> | null]>([
    [{ staging_hints: { media_x: 0.25 } }, { ...initialStaging, media_x: 0.25 }],
    [
      { staging_hints: { media_visibility: { preference_id: 'sprites', values: [false] } } },
      { ...initialStaging, media_visibility: { preference_id: 'sprites', values: [false] } },
    ],
    [
      { staging_hints: { media_y: null, media_timing: null } },
      { ...initialStaging, media_y: null, media_timing: null },
    ],
    [{ staging_hints: null }, null],
    [{ staging_hints: {} }, initialStaging],
    [{ text: 'A caption' }, initialStaging],
  ])('preserves omitted hint coordinates and explicit null clears for %j', (payload, expected) => {
    const original: StoryFragment = {
      uid: 'alice',
      fragment_type: 'media',
      rit_id: 'portrait',
      source_id: 'source',
      presentation_handle: 'character:alice',
      staging_hints: initialStaging,
    }
    const before = JSON.stringify(original)
    const state: Record<string, StoryFragment> = { alice: original }
    applyControlFragment(state, {
      uid: 'move',
      fragment_type: 'update',
      target: { kind: 'handle', handle: 'character:alice' },
      patch_kind: 'presentation',
      payload,
    })
    expect(state.alice?.staging_hints).toEqual(expected)
    expect(state.alice).toMatchObject({ uid: 'alice', rit_id: 'portrait', source_id: 'source' })
    expect(JSON.stringify(original)).toBe(before)
  })

  it.each(['hints', 'presentation_hints'])('merges only the named %s container', (field) => {
    const state: Record<string, StoryFragment> = {
      text: {
        uid: 'text',
        fragment_type: 'content',
        content: { a: 1 },
        hints: { style_name: 'speaker', icon: 'old' },
      },
    }
    applyControlFragment(state, {
      uid: 'icon',
      fragment_type: 'update',
      target: { kind: 'fragment', fragment_id: 'text' },
      patch_kind: 'presentation',
      payload: { [field]: { icon: null } },
    })
    expect(state.text?.hints).toEqual({ style_name: 'speaker', icon: null })
    applyControlFragment(state, {
      uid: 'clear',
      fragment_type: 'update',
      target: { kind: 'fragment', fragment_id: 'text' },
      patch_kind: 'presentation',
      payload: { [field]: null },
    })
    expect(state.text?.hints).toBeNull()
    applyControlFragment(state, {
      uid: 'game',
      fragment_type: 'update',
      target: { kind: 'fragment', fragment_id: 'text' },
      payload: { content: { b: 2 } },
    })
    expect(state.text?.content).toEqual({ b: 2 })
  })
})
