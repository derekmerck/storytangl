import type {
  BaseStoryFragment,
  ChoiceStoryFragment,
  ControlStoryFragment,
  FragmentId,
  GroupStoryFragment,
  MediaStoryFragment,
  RuntimeEnvelope,
  StoryFragment,
  PieceStoryFragment,
  RollStoryFragment,
} from '@/types'

export type UnknownRecord = Record<string, unknown>

export const isRecord = (value: unknown): value is UnknownRecord =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

export const isRuntimeEnvelope = (payload: unknown): payload is RuntimeEnvelope =>
  isRecord(payload) && Array.isArray(payload.fragments)

export const isGroupFragment = (fragment: StoryFragment): fragment is GroupStoryFragment =>
  (fragment.fragment_type === 'group' || fragment.fragment_type === 'dialog') &&
  Array.isArray((fragment as GroupStoryFragment).member_ids)

export const isChoiceFragment = (fragment: StoryFragment): fragment is ChoiceStoryFragment =>
  fragment.fragment_type === 'choice'

export const isMediaFragment = (fragment: StoryFragment): fragment is MediaStoryFragment =>
  fragment.fragment_type === 'media'

export const isPieceFragment = (fragment: StoryFragment): fragment is PieceStoryFragment =>
  fragment.fragment_type === 'piece'

export const isRollFragment = (fragment: StoryFragment): fragment is RollStoryFragment =>
  fragment.fragment_type === 'roll'

export const isControlFragment = (fragment: StoryFragment): fragment is ControlStoryFragment =>
  fragment.fragment_type === 'update' || fragment.fragment_type === 'delete'

export const fragmentText = (value: unknown): string => {
  if (typeof value === 'string') {
    return value
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }
  if (value === null || value === undefined) {
    return ''
  }
  return JSON.stringify(value)
}

export const applyControlFragment = (
  registry: Record<string, StoryFragment>,
  fragment: ControlStoryFragment,
): void => {
  if (fragment.media_action) return // Playback owners, not historical views, consume restart.
  for (const [id, existing] of Object.entries(registry)) {
    const target = fragment.target
    const matches =
      target.kind === 'fragment'
        ? id === target.fragment_id
        : isMediaFragment(existing) &&
          (target.kind === 'rit'
            ? existing.rit_id === target.rit_id
            : target.kind === 'role'
              ? existing.media_role === target.media_role
              : existing.presentation_handle === target.handle)
    if (!matches) continue
    if (fragment.fragment_type === 'delete') delete registry[id]
    else {
      let updated: StoryFragment = existing
      if (fragment.media && isMediaFragment(existing)) {
        updated = { ...fragment.media, uid: id }
      } else if (isRecord(fragment.payload) && !fragment.media) {
        if (isMediaFragment(existing) && fragment.patch_kind !== 'presentation') continue
        updated = { ...existing, ...fragment.payload, uid: id } as StoryFragment
        if (fragment.patch_kind === 'presentation') {
          for (const key of ['staging_hints', 'hints'] as const) {
            const patch =
              key === 'hints' && !('hints' in fragment.payload)
                ? fragment.payload.presentation_hints
                : fragment.payload[key]
            if (
              key === 'hints' &&
              ('hints' in fragment.payload || 'presentation_hints' in fragment.payload)
            ) {
              updated.hints = patch
              delete updated.presentation_hints
            }
            if (isRecord(patch)) {
              const previous =
                key === 'hints' ? (existing.hints ?? existing.presentation_hints) : existing[key]
              updated[key] = { ...(isRecord(previous) ? previous : {}), ...patch }
            }
          }
        }
      }
      if (
        isMediaFragment(existing) &&
        isMediaFragment(updated) &&
        fragment.media &&
        existing.rit_id &&
        existing.rit_id === updated.rit_id &&
        existing.staging_hints?.media_timing != null &&
        updated.staging_hints?.media_timing == null
      ) {
        updated = {
          ...updated,
          staging_hints: {
            ...updated.staging_hints,
            media_timing: existing.staging_hints.media_timing,
          },
        }
      }
      registry[id] = updated
    }
  }
}

export const fragmentUid = (
  fragment: unknown,
  options: { fallbackPrefix: string; index: number },
): FragmentId => {
  if (isRecord(fragment) && typeof fragment.uid === 'string' && fragment.uid) {
    return fragment.uid
  }
  return `${options.fallbackPrefix}-${options.index + 1}`
}

export const coerceStoryFragment = (
  fragment: unknown,
  options: { fallbackPrefix: string; index: number },
): StoryFragment => {
  if (!isRecord(fragment)) {
    return {
      uid: `${options.fallbackPrefix}-unknown-${options.index + 1}`,
      fragment_type: 'unknown',
      content: fragment,
    } satisfies BaseStoryFragment
  }

  const fragmentType =
    typeof fragment.fragment_type === 'string' && fragment.fragment_type
      ? fragment.fragment_type
      : 'unknown'

  return {
    ...fragment,
    uid: fragmentUid(fragment, options),
    fragment_type: fragmentType,
  } as StoryFragment
}

const coerceFragmentStream = (
  fragments: unknown[],
  options: { fallbackPrefix: string },
): StoryFragment[] =>
  fragments.map((fragment, index) =>
    coerceStoryFragment(fragment, { fallbackPrefix: options.fallbackPrefix, index }),
  )

export const normalizeEnvelope = (
  payload: unknown,
  options: { fallbackPrefix: string },
): RuntimeEnvelope | null => {
  if (!isRuntimeEnvelope(payload)) {
    return null
  }

  return {
    cursor_id: typeof payload.cursor_id === 'string' ? payload.cursor_id : null,
    step: typeof payload.step === 'number' ? payload.step : null,
    fragments: coerceFragmentStream(payload.fragments, options),
    ux_events: Array.isArray(payload.ux_events) ? payload.ux_events : [],
    last_redirect: payload.last_redirect ?? null,
    redirect_trace: payload.redirect_trace ?? [],
    metadata: payload.metadata ?? {},
    presentation: payload.presentation,
  }
}

/** A blank string is not a source; treat it as absent so callers need not. */
const nonEmpty = (value: unknown): string | undefined =>
  typeof value === 'string' && value.length > 0 ? value : undefined

export const mediaContentUrl = (fragment: MediaStoryFragment): string | undefined => {
  if (fragment.content_format === 'url') {
    const contentUrl = nonEmpty(fragment.content)
    if (contentUrl !== undefined) {
      return contentUrl
    }
  }
  const named = nonEmpty(fragment.url) ?? nonEmpty(fragment.src)
  if (named !== undefined) {
    return named
  }
  if (isRecord(fragment.content)) {
    return nonEmpty(fragment.content.url) ?? nonEmpty(fragment.content.src)
  }
  return undefined
}

export const mediaData = (fragment: MediaStoryFragment): unknown => {
  if (fragment.data !== undefined) {
    return fragment.data
  }
  if (fragment.content_format === 'data') {
    return fragment.content
  }
  if (isRecord(fragment.content)) {
    return fragment.content.data
  }
  return undefined
}
