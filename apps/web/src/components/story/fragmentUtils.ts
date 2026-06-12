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

export const fragmentRefId = (fragment: ControlStoryFragment): FragmentId | undefined => {
  const value = fragment.ref_id ?? fragment.reference_id
  return typeof value === 'string' && value ? value : undefined
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
  }
}

export const mediaContentUrl = (fragment: MediaStoryFragment): string | undefined => {
  if (fragment.content_format === 'url' && typeof fragment.content === 'string') {
    return fragment.content
  }
  if (typeof fragment.url === 'string') {
    return fragment.url
  }
  if (typeof fragment.src === 'string') {
    return fragment.src
  }
  if (isRecord(fragment.content)) {
    const contentUrl = fragment.content.url ?? fragment.content.src
    return typeof contentUrl === 'string' ? contentUrl : undefined
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
