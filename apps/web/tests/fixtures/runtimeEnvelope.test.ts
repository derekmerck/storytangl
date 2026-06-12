import { describe, expect, it } from 'vitest'

import {
  buyQuantityRuntimeEnvelope,
  commandHintRuntimeEnvelope,
  composePayloadRuntimeEnvelope,
  crossroadsRuntimeEnvelope,
  sandboxPayloadRuntimeEnvelope,
} from '.'
import type {
  ChoiceStoryFragment,
  GroupStoryFragment,
  RuntimeEnvelope,
  StoryFragment,
} from '@/types'

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

const isGroup = (fragment: StoryFragment | undefined): fragment is GroupStoryFragment => {
  if (!fragment) {
    return false
  }
  return (
    (fragment.fragment_type === 'group' || fragment.fragment_type === 'dialog') &&
    Array.isArray((fragment as GroupStoryFragment).member_ids)
  )
}

const isOpenChoice = (fragment: StoryFragment): fragment is ChoiceStoryFragment =>
  fragment.fragment_type === 'choice' && fragment.available !== false

const collectReferenceIds = (value: unknown, parentKey = ''): string[] => {
  if (typeof value === 'string') {
    return parentKey.endsWith('_ref') || parentKey.endsWith('_id') ? [value] : []
  }
  if (Array.isArray(value)) {
    return value.flatMap((item) => collectReferenceIds(item, parentKey))
  }
  if (!isRecord(value)) {
    return []
  }
  return Object.entries(value).flatMap(([key, item]) => {
    if (key.endsWith('_refs') || key.endsWith('_ids')) {
      return Array.isArray(item)
        ? item.filter((entry): entry is string => typeof entry === 'string')
        : []
    }
    return collectReferenceIds(item, key)
  })
}

const renderableIdsByScene = (envelope: RuntimeEnvelope): Array<Set<string>> => {
  const fragmentsById = new Map(envelope.fragments.map((fragment) => [fragment.uid, fragment]))
  const sceneGroups = envelope.fragments.filter(
    (fragment): fragment is GroupStoryFragment =>
      isGroup(fragment) && fragment.group_type === 'scene',
  )

  return sceneGroups.map((scene) => {
    const visible = new Set<string>()
    const visit = (id: string) => {
      if (visible.has(id)) {
        return
      }
      visible.add(id)
      const fragment = fragmentsById.get(id)
      if (isGroup(fragment)) {
        fragment.member_ids.forEach(visit)
      }
    }
    scene.member_ids.forEach(visit)
    return visible
  })
}

describe('runtime envelope fixtures', () => {
  it('keeps open choice references renderable in the current scene shell', () => {
    const envelopes = [
      crossroadsRuntimeEnvelope,
      buyQuantityRuntimeEnvelope,
      sandboxPayloadRuntimeEnvelope,
      commandHintRuntimeEnvelope,
    ]
    const referencedChoices: Array<{ choice: ChoiceStoryFragment; refs: string[] }> = []

    for (const envelope of envelopes) {
      const sceneRenderableIds = renderableIdsByScene(envelope)
      const envelopeReferencedChoices: Array<{ choice: ChoiceStoryFragment; refs: string[] }> = []

      for (const fragment of envelope.fragments) {
        if (!isOpenChoice(fragment)) {
          continue
        }
        const accepts: Record<string, unknown> = isRecord(fragment.accepts) ? fragment.accepts : {}
        const refs = collectReferenceIds(accepts)
        if (refs.length > 0) {
          const entry = { choice: fragment, refs }
          referencedChoices.push(entry)
          envelopeReferencedChoices.push(entry)
        }
      }

      for (const { choice, refs } of envelopeReferencedChoices) {
        const scene = sceneRenderableIds.find((ids) => ids.has(choice.uid))
        expect(scene, `choice ${choice.uid} must be inside a scene group`).toBeDefined()
        for (const ref of refs) {
          expect(scene!.has(ref), `choice ${choice.uid} references hidden state ${ref}`).toBe(true)
        }
      }
    }

    expect(referencedChoices).not.toHaveLength(0)
  })

  it('covers text, quantity, piece, and raw command payload accepts', () => {
    const kinds = new Set(
      [
        ...sandboxPayloadRuntimeEnvelope.fragments,
        ...commandHintRuntimeEnvelope.fragments,
        ...composePayloadRuntimeEnvelope.fragments,
      ]
        .filter((fragment): fragment is ChoiceStoryFragment => fragment.fragment_type === 'choice')
        .map((choice) =>
          isRecord(choice.accepts) && typeof choice.accepts.kind === 'string'
            ? choice.accepts.kind
            : undefined,
        )
        .filter((kind): kind is NonNullable<typeof kind> => typeof kind === 'string'),
    )

    expect(kinds.has('text')).toBe(true)
    expect(kinds.has('quantity')).toBe(true)
    expect(kinds.has('pieces')).toBe(true)
    expect(kinds.has('compose')).toBe(true)
    expect(commandHintRuntimeEnvelope.ux_events?.[0]?.presentation).toBe('inline')
  })

  it('keeps command grammar hints advisory metadata', () => {
    const grammar = commandHintRuntimeEnvelope.metadata?.grammar

    expect(isRecord(grammar)).toBe(true)
    if (!isRecord(grammar)) {
      throw new Error('command grammar fixture must be an object')
    }
    expect(Array.isArray(grammar.examples)).toBe(true)
    expect(grammar.examples).toContain('take lamp')
  })
})
