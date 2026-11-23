import type { MediaStoryFragment } from '@/types'
import { mediaRole } from './fragmentViewUtils'

/**
 * Client policy for folding a stream of steps into one stage. Not a stream
 * contract, and deliberately minimal: #409 replaces it with authoritative stage
 * handles and update/delete controls, and this file is what that work deletes.
 *
 * A step that states the room -- a backdrop or any `staged_im` -- replaces the
 * stage with what it stages. A step that states no room keeps the stage, and
 * any figures it brings join it. The pygame client's `merge_turns` folds the
 * same way and goes further (speaker-keyed portraits, inherited staging); that
 * is its own policy, not ported here.
 */
const ROOM_ROLES = ['narrative_im', 'staged_im']

export const foldStage = (
  stage: MediaStoryFragment[],
  step: MediaStoryFragment[]
): MediaStoryFragment[] =>
  step.some((image) => ROOM_ROLES.includes(mediaRole(image))) ? step : [...stage, ...step]
