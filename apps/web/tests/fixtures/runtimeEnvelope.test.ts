import { describe, expect, it } from 'vitest'

import { crossroadsRuntimeEnvelope } from './runtimeEnvelope'
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
    const sceneRenderableIds = renderableIdsByScene(crossroadsRuntimeEnvelope)
    const referencedChoices: Array<{ choice: ChoiceStoryFragment; refs: string[] }> = []

    for (const fragment of crossroadsRuntimeEnvelope.fragments) {
      if (!isOpenChoice(fragment)) {
        continue
      }
      const refs = collectReferenceIds(fragment.accepts?.constraints)
      if (refs.length > 0) {
        referencedChoices.push({ choice: fragment, refs })
      }
    }

    expect(referencedChoices).not.toHaveLength(0)

    for (const { choice, refs } of referencedChoices) {
      const scene = sceneRenderableIds.find((ids) => ids.has(choice.uid))
      expect(scene, `choice ${choice.uid} must be inside a scene group`).toBeDefined()
      for (const ref of refs) {
        expect(scene!.has(ref), `choice ${choice.uid} references hidden state ${ref}`).toBe(true)
      }
    }
  })
})
