import type { KvRow, MediaStoryFragment, PrimitiveValue, StoryFragment } from '@/types'
import { mediaContentUrl, mediaData } from './fragmentUtils'

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

/**
 * Pending means the service could not give us a source, not that the fragment
 * started life as a RIT. `content_format` describes what a payload carries, so
 * a resolved generated image arrives as `url` like any other -- sniffing for
 * `'rit'` here placeholdered every generated image the service had already
 * dereferenced.
 */
export const isPendingMedia = (fragment: MediaStoryFragment): boolean =>
  mediaContentUrl(fragment) === undefined && mediaData(fragment) === undefined

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
