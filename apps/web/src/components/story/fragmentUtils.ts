import type {
  BaseStoryFragment,
  ChoiceStoryFragment,
  ControlStoryFragment,
  FragmentId,
  GroupStoryFragment,
  MediaStoryFragment,
  RuntimeEnvelope,
  StoryFragment,
  TokenStoryFragment,
} from '@/types'

export type UnknownRecord = Record<string, unknown>

export const isRecord = (value: unknown): value is UnknownRecord =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

export const isRuntimeEnvelope = (payload: unknown): payload is RuntimeEnvelope =>
  isRecord(payload) && Array.isArray(payload.fragments)

const isLegacyStoryBlock = (value: unknown): value is UnknownRecord => {
  if (!isRecord(value)) {
    return false
  }
  return (
    typeof value.text === 'string' ||
    typeof value.title === 'string' ||
    Array.isArray(value.media) ||
    Array.isArray(value.dialog) ||
    Array.isArray(value.actions)
  )
}

export const isGroupFragment = (fragment: StoryFragment): fragment is GroupStoryFragment =>
  (fragment.fragment_type === 'group' || fragment.fragment_type === 'dialog') &&
  Array.isArray((fragment as GroupStoryFragment).member_ids)

export const isChoiceFragment = (fragment: StoryFragment): fragment is ChoiceStoryFragment =>
  fragment.fragment_type === 'choice'

export const isMediaFragment = (fragment: StoryFragment): fragment is MediaStoryFragment =>
  fragment.fragment_type === 'media'

export const isTokenFragment = (fragment: StoryFragment): fragment is TokenStoryFragment =>
  fragment.fragment_type === 'token'

export const isControlFragment = (fragment: StoryFragment): fragment is ControlStoryFragment =>
  fragment.fragment_type === 'update' || fragment.fragment_type === 'delete'

export const isUserEventFragment = (fragment: StoryFragment) =>
  fragment.fragment_type === 'user_event'

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

const legacyMediaToFragments = (
  media: unknown,
  options: { uidPrefix: string },
): StoryFragment[] => {
  if (!Array.isArray(media)) {
    return []
  }

  return media
    .filter(isRecord)
    .map((item, index) => ({
      uid: `${options.uidPrefix}-media-${index + 1}`,
      fragment_type: 'media',
      content: item.url ?? item.data ?? item.src ?? '',
      content_format: item.url || item.src ? 'url' : 'data',
      media_role: typeof item.media_role === 'string' ? item.media_role : 'narrative_im',
      staging_hints: {
        media_shape: item.orientation,
      },
    })) as StoryFragment[]
}

const legacyDialogToFragments = (
  dialog: unknown,
  options: { uidPrefix: string },
): StoryFragment[] => {
  if (!Array.isArray(dialog) || dialog.length === 0) {
    return []
  }

  const fragments: StoryFragment[] = []
  const memberIds: string[] = []

  dialog.filter(isRecord).forEach((item, index) => {
    const lineUid = `${options.uidPrefix}-dialog-${index + 1}`
    memberIds.push(lineUid)
    fragments.push({
      uid: lineUid,
      fragment_type: 'attributed',
      who: typeof item.label === 'string' ? item.label : '',
      how: '',
      media: 'speech',
      content: item.text ?? item.content ?? '',
    })

    const mediaFragments = legacyMediaToFragments(item.media, {
      uidPrefix: `${options.uidPrefix}-dialog-${index + 1}`,
    })
    for (const mediaFragment of mediaFragments) {
      memberIds.push(mediaFragment.uid)
      fragments.push(mediaFragment)
    }
  })

  return [
    {
      uid: `${options.uidPrefix}-dialog-group`,
      fragment_type: 'group',
      group_type: 'dialog',
      member_ids: memberIds,
    },
    ...fragments,
  ]
}

const legacyActionsToFragments = (
  actions: unknown,
  options: { uidPrefix: string },
): StoryFragment[] => {
  if (!Array.isArray(actions)) {
    return []
  }

  return actions.filter(isRecord).map((action, index) => ({
    uid: `${options.uidPrefix}-choice-${index + 1}`,
    fragment_type: 'choice',
    edge_id: typeof action.uid === 'string' ? action.uid : `${options.uidPrefix}-edge-${index + 1}`,
    text: typeof action.text === 'string' ? action.text : 'Continue',
    available: true,
    payload: action.passback ?? action.payload,
    ui_hints: action.ui_hints,
  })) as StoryFragment[]
}

const legacyBlockToFragments = (
  block: UnknownRecord,
  options: { fallbackPrefix: string; index: number },
): StoryFragment[] => {
  const uidPrefix =
    typeof block.uid === 'string' && block.uid
      ? block.uid
      : `${options.fallbackPrefix}-legacy-${options.index + 1}`
  const fragments: StoryFragment[] = []
  const memberIds: string[] = []

  if (typeof block.title === 'string' && block.title) {
    const titleUid = `${uidPrefix}-title`
    memberIds.push(titleUid)
    fragments.push({
      uid: titleUid,
      fragment_type: 'content',
      content: block.title,
      hints: { style_tags: ['title'] },
    })
  }

  if (typeof block.text === 'string' && block.text) {
    const contentUid = `${uidPrefix}-content`
    memberIds.push(contentUid)
    fragments.push({
      uid: contentUid,
      fragment_type: 'content',
      content: block.text,
      content_format: 'html',
    })
  }

  const mediaFragments = legacyMediaToFragments(block.media, { uidPrefix })
  mediaFragments.forEach((fragment) => memberIds.push(fragment.uid))
  fragments.push(...mediaFragments)

  const dialogFragments = legacyDialogToFragments(block.dialog, { uidPrefix })
  if (dialogFragments.length > 0) {
    memberIds.push(dialogFragments[0]!.uid)
    fragments.push(...dialogFragments)
  }

  const choiceFragments = legacyActionsToFragments(block.actions, { uidPrefix })
  choiceFragments.forEach((fragment) => memberIds.push(fragment.uid))
  fragments.push(...choiceFragments)

  return [
    {
      uid: `${uidPrefix}-scene`,
      fragment_type: 'group',
      group_type: 'scene',
      member_ids: memberIds,
    },
    ...fragments,
  ]
}

const coerceFragmentStream = (
  fragments: unknown[],
  options: { fallbackPrefix: string },
): StoryFragment[] =>
  fragments.flatMap((fragment, index) => {
    if (isLegacyStoryBlock(fragment) && !('fragment_type' in fragment)) {
      return legacyBlockToFragments(fragment, { fallbackPrefix: options.fallbackPrefix, index })
    }
    return [coerceStoryFragment(fragment, { fallbackPrefix: options.fallbackPrefix, index })]
  })

export const normalizeEnvelope = (
  payload: unknown,
  options: { fallbackPrefix: string },
): RuntimeEnvelope | null => {
  if (Array.isArray(payload)) {
    return {
      cursor_id: null,
      step: null,
      fragments: coerceFragmentStream(payload, options),
      last_redirect: null,
      redirect_trace: [],
      metadata: { compatibility_adapter: 'JournalStoryUpdate[]' },
    }
  }

  if (!isRuntimeEnvelope(payload)) {
    return null
  }

  return {
    cursor_id: typeof payload.cursor_id === 'string' ? payload.cursor_id : null,
    step: typeof payload.step === 'number' ? payload.step : null,
    fragments: coerceFragmentStream(payload.fragments, options),
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
