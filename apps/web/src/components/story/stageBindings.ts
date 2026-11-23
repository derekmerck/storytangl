import type { ClipBinding, MediaStoryFragment, VisibilityBinding } from '@/types'
import type { PreferenceValues } from '@/worldPreferences'

/**
 * How a viewer's local preferences resolve staging bindings. A port of
 * `VisibilityBinding.admits` and `ClipBinding.select` in
 * `tangl.presentation.hints`; both are pinned by the shared cases in
 * `engine/tests/presentation/staging_bindings.json`. A preference this browser
 * has no value for yet matches nothing, so bound art waits for its declaration.
 */
export const admits = (binding: VisibilityBinding, preferences: PreferenceValues): boolean =>
  binding.values.includes(preferences[binding.preference_id]!)

export const selectClip = (
  binding: ClipBinding,
  preferences: PreferenceValues
): string | undefined =>
  binding.rows.find((row) =>
    binding.axes.every((axis, index) => row.values[index] === preferences[axis])
  )?.clip

/** Whether the viewer sees this media: unbound media always shows. */
export const isVisible = (fragment: MediaStoryFragment, preferences: PreferenceValues): boolean => {
  const binding = fragment.staging_hints?.media_visibility
  return !binding || admits(binding, preferences)
}

/**
 * The clip this use would play: the bound row for the viewer's values, else the
 * authored `media_clip`. Resolved and recorded only; sheet playback comes later.
 */
export const selectedClip = (
  fragment: MediaStoryFragment,
  preferences: PreferenceValues
): string | undefined => {
  const hints = fragment.staging_hints
  const bound = hints?.media_clip_binding && selectClip(hints.media_clip_binding, preferences)
  return bound ?? hints?.media_clip ?? undefined
}
