import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

import type { ClipBinding, VisibilityBinding } from '@/types'
import type { PreferenceValues } from '@/worldPreferences'
import { reparteeClerk } from '@tests/fixtures'
import { admits, isVisible, selectClip, selectedClip } from './stageBindings'

interface Case<B, R> {
  name: string
  binding: B
  preferences: PreferenceValues
  admits: R
  clip: R
}

// The cases the Python rules in tangl.presentation.hints are tested against.
const shared = JSON.parse(
  readFileSync(
    resolve(__dirname, '../../../../../engine/tests/presentation/staging_bindings.json'),
    'utf8'
  )
) as {
  visibility: Case<VisibilityBinding, boolean>[]
  clip: Case<ClipBinding, string | null>[]
}

describe('staging bindings agree with tangl.presentation.hints', () => {
  it.each(shared.visibility.map((item) => [item.name, item] as const))(
    'visibility: %s',
    (_name, item) => {
      expect(admits(item.binding, item.preferences)).toBe(item.admits)
    }
  )

  it.each(shared.clip.map((item) => [item.name, item] as const))('clip: %s', (_name, item) => {
    expect(selectClip(item.binding, item.preferences) ?? null).toBe(item.clip)
  })
})

describe('repartee_loop clerk', () => {
  it('waits for a preference this browser has no value for yet', () => {
    expect(isVisible(reparteeClerk, {})).toBe(false)
  })

  it('follows its bound preferences, and keeps its authored clip with no row', () => {
    const on = { 'sprites-visible': true, 'clerk-motion': 'response' }
    expect(isVisible(reparteeClerk, on)).toBe(true)
    expect(isVisible(reparteeClerk, { ...on, 'sprites-visible': false })).toBe(false)
    expect(selectedClip(reparteeClerk, on)).toBe('response')
    expect(selectedClip(reparteeClerk, { 'clerk-motion': 'dance' })).toBe('idle')
  })
})
