import type { MediaStoryFragment } from '@/types'
import { mediaRole } from './fragmentViewUtils'

/**
 * Client policy for folding a stream of steps into one stage. Not a stream
 * contract, and deliberately minimal: #409 replaces it with authoritative stage
 * handles and update/delete controls, and this file is what that work deletes.
 *
 * A step that states the room -- a backdrop or any `staged_im` -- replaces the
 * stage with what it stages. A step that states no room keeps the stage, and
 * any figures it brings join it. That holds across scene boundaries once #726
 * has containers state their room on entry by any path. The pygame client's
 * `merge_turns` folds the same way and goes further (speaker-keyed portraits,
 * inherited staging); that is its own policy, not ported here.
 *
 * Steps are runs of equal journal `step`, which the service delivers on each
 * fragment, as pygame's `build_turns` groups them. One update (one envelope)
 * may hold several steps, and a restored history is one flat envelope, so the
 * update is not the unit: folding by `step` makes restored play stage what live
 * play did.
 */
const ROOM_ROLES = ['narrative_im', 'staged_im']

export const foldStage = (
  stage: MediaStoryFragment[],
  step: MediaStoryFragment[]
): MediaStoryFragment[] =>
  step.some((image) => ROOM_ROLES.includes(mediaRole(image))) ? step : [...stage, ...step]

export const foldSteps = (images: MediaStoryFragment[]): MediaStoryFragment[] => {
  const steps: MediaStoryFragment[][] = []
  images.forEach((image, index) => {
    if (index === 0 || image.step !== images[index - 1]!.step) steps.push([])
    steps.at(-1)!.push(image)
  })
  return steps.reduce(foldStage, [])
}
