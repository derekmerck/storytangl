import type { KvRow, MediaStoryFragment, PrimitiveValue, StoryFragment } from '@/types'

export const contentClass = (fragment: StoryFragment): string[] => {
  const hints = fragment.hints ?? fragment.presentation_hints
  if (!hints || typeof hints !== 'object' || !('style_tags' in hints)) {
    return []
  }
  return Array.isArray(hints.style_tags)
    ? hints.style_tags.map((tag) => `story-style-${tag}`)
    : []
}

export const kvItems = (fragment: StoryFragment): KvRow[] => {
  if (fragment.fragment_type !== 'kv' || !Array.isArray(fragment.content)) {
    return []
  }
  const isPrimitiveValue = (value: unknown): value is PrimitiveValue =>
    typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean'

  return fragment.content.filter(
    (item): item is KvRow =>
      item !== null &&
      typeof item === 'object' &&
      'key' in item &&
      typeof item.key === 'string' &&
      'value' in item &&
      isPrimitiveValue(item.value),
  )
}

export const mediaRole = (fragment: MediaStoryFragment): string =>
  typeof fragment.media_role === 'string' && fragment.media_role
    ? fragment.media_role
    : 'media'

export type MediaElement = 'img' | 'audio' | 'video'

const MEDIA_ELEMENTS: Record<string, MediaElement> = {
  image: 'img',
  vector: 'img',
  audio: 'audio',
  video: 'video',
}

/**
 * The element that can play this payload, chosen by what it is (`media_type`),
 * never by what it is for (`media_role`): a `character_vox` bark is audio
 * whatever its role is called. `undefined` means no element here can play it,
 * and the view falls back to an explicit placeholder rather than guessing.
 */
export const mediaElement = (fragment: MediaStoryFragment): MediaElement | undefined =>
  MEDIA_ELEMENTS[fragment.media_type ?? '']

const mediaShape = (fragment: MediaStoryFragment): string | undefined => {
  const shape = fragment.staging_hints?.media_shape
  if (typeof shape === 'string') {
    return shape
  }
  const orientation = fragment.orientation
  return typeof orientation === 'string' ? orientation : undefined
}

export const hasLandscapeShape = (fragment: MediaStoryFragment): boolean =>
  ['landscape', 'banner', 'cover', 'bg'].includes(mediaShape(fragment) ?? '')
