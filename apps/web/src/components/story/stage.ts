import type { MediaStoryFragment } from '@/types'
import type { PreferenceValues } from '@/worldPreferences'
import { mediaContentUrl } from './fragmentUtils'
import { mediaElement, mediaRole } from './fragmentViewUtils'
import { isVisible } from './stageBindings'

/**
 * What the stage draws and where. The semantics follow the pygame client's
 * `stage.py`; the code does not, since CSS places by edges and transforms
 * rather than by measured pixel boxes.
 */

export interface StageExtent {
  width: number
  height: number
}

/** pygame's `_DEFAULT_LOGICAL_SIZE`, for a world that declares no `stage_extent`. */
export const DEFAULT_STAGE_EXTENT: StageExtent = { width: 320, height: 200 }

export const BACKDROP_ROLE = 'narrative_im'
const FIGURE_ROLES = ['staged_im', 'dialog_im']

/**
 * How many figures one stage draws: pygame's `STAGED_LIMIT`. A bound, not a
 * design limit, so a world that generates its cast degrades by dropping the tail.
 */
export const STAGED_LIMIT = 12

/** pygame's `_DEFAULT_SLOTS`: where unplaced dialog figures stand, by arrival. */
const DEFAULT_SLOTS = ['left', 'right', 'mid'] as const

/**
 * Whether the stage, rather than the text flow, owns this media: a backdrop or
 * a figure the browser can draw. One without a source stays in the flow, where
 * its placeholder says so.
 */
export const isStagedMedia = (fragment: MediaStoryFragment): boolean =>
  [BACKDROP_ROLE, ...FIGURE_ROLES].includes(mediaRole(fragment)) &&
  mediaElement(fragment) === 'img' &&
  mediaContentUrl(fragment) !== undefined

/**
 * What the viewer sees: the last visible backdrop, and the visible figures in
 * arrival order, capped. Each figure keeps its arrival index among dialog
 * figures, counted before hiding, so hiding one does not move the others; the
 * cap counts only what is drawn. Both as pygame's stage does.
 */
export const castStage = (images: MediaStoryFragment[], preferences: PreferenceValues) => {
  let dialogIndex = 0
  return {
    backdrop: images
      .filter((image) => mediaRole(image) === BACKDROP_ROLE && isVisible(image, preferences))
      .at(-1),
    figures: images
      .filter((image) => FIGURE_ROLES.includes(mediaRole(image)))
      .map((figure) => ({
        figure,
        index: mediaRole(figure) === 'dialog_im' ? dialogIndex++ : 0,
      }))
      .filter(({ figure }) => isVisible(figure, preferences))
      .slice(0, STAGED_LIMIT),
  }
}

/**
 * CSS placing one figure, drawn at its natural size, on a stage of `extent`
 * logical pixels. A fraction is exact: `media_x` places the centre and
 * `media_y` the bottom, unclamped, since off stage is a real position. A name
 * is a station: `left`/`right` stand a gutter in from the edge, `mid` centres,
 * and an unknown name centres. Without `media_y` a figure stands on the floor.
 * `index` is the figure's arrival order among dialog figures, which picks an
 * unplaced one's station as pygame does.
 */
export const figureStyle = (
  fragment: MediaStoryFragment,
  index: number,
  extent: StageExtent
): Record<string, string> => {
  const hints = fragment.staging_hints ?? {}
  const gutter = `${extent.width / 32}px` // pygame's 10px at 320 wide
  const style: Record<string, string> = {}
  const transform: string[] = []

  const x =
    hints.media_x ??
    (mediaRole(fragment) === 'dialog_im'
      ? DEFAULT_SLOTS[Math.min(index, DEFAULT_SLOTS.length - 1)]
      : 'mid')
  if (typeof x === 'number') {
    style.left = `${x * extent.width}px`
    transform.push('translateX(-50%)')
  } else if (x === 'left') {
    style.left = gutter
  } else if (x === 'right') {
    style.right = gutter
  } else {
    style.left = '50%'
    transform.push('translateX(-50%)')
  }

  const y = hints.media_y
  if (typeof y === 'number') {
    style.top = `${y * extent.height}px`
    transform.push('translateY(-100%)')
  } else if (y === 'top') {
    style.top = gutter
  } else if (y === 'mid') {
    style.top = '50%'
    transform.push('translateY(-50%)')
  } else {
    style.bottom = '0'
  }

  if (hints.media_flip_h === true) transform.push('scaleX(-1)')
  if (transform.length) style.transform = transform.join(' ')
  return style
}
