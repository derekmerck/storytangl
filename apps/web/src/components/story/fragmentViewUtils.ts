import type { MediaStoryFragment, StoryFragment } from '@/types'

export const contentClass = (fragment: StoryFragment): string[] => {
  const hints = fragment.hints ?? fragment.presentation_hints
  if (!hints || typeof hints !== 'object' || !('style_tags' in hints)) {
    return []
  }
  return Array.isArray(hints.style_tags)
    ? hints.style_tags.map((tag) => `story-style-${tag}`)
    : []
}

export const kvItems = (fragment: StoryFragment): Array<[string, unknown]> => {
  if (fragment.fragment_type !== 'kv' || !Array.isArray(fragment.content)) {
    return []
  }
  return fragment.content.filter(
    (item): item is [string, unknown] =>
      Array.isArray(item) && typeof item[0] === 'string' && item.length >= 2,
  )
}

export const mediaRole = (fragment: MediaStoryFragment): string =>
  typeof fragment.media_role === 'string' && fragment.media_role
    ? fragment.media_role
    : 'media'

export const isPendingMedia = (fragment: MediaStoryFragment): boolean =>
  fragment.content_format === 'rit' || fragment.generation_status === 'pending'

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
