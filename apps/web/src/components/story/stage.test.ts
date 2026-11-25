import { describe, expect, it } from 'vitest'

import type { MediaStoryFragment, StagingHints } from '@/types'
import { castStage, figureStyle, isStagedMedia, STAGED_LIMIT } from './stage'
import { foldStage, foldSteps } from './stageFold'

const extent = { width: 640, height: 400 }
const image = (
  uid: string,
  role: string,
  hints: StagingHints = {},
  step?: number
): MediaStoryFragment => ({
  uid,
  step,
  fragment_type: 'media',
  media_type: 'image',
  media_role: role,
  content_format: 'url',
  url: `/media/${uid}.png`,
  staging_hints: hints,
})

describe('figureStyle', () => {
  it('places a numeric media_x at the centre and media_y at the bottom edge', () => {
    expect(figureStyle(image('a', 'staged_im', { media_x: 0.25, media_y: 0.9 }), 0, extent)).toEqual(
      { left: '160px', top: '360px', transform: 'translateX(-50%) translateY(-100%)' }
    )
  })

  it('honours a fraction off stage, unclamped', () => {
    expect(figureStyle(image('a', 'staged_im', { media_x: -0.5 }), 0, extent).left).toBe('-320px')
  })

  it.each([
    ['left', { left: '20px', bottom: '0' }],
    ['right', { right: '20px', bottom: '0' }],
    ['mid', { left: '50%', bottom: '0', transform: 'translateX(-50%)' }],
    ['downstage', { left: '50%', bottom: '0', transform: 'translateX(-50%)' }],
  ])('stands a figure named %s at its station', (station, style) => {
    const hints = { media_x: station } as StagingHints
    expect(figureStyle(image('a', 'staged_im', hints), 0, extent)).toEqual(style)
  })

  it.each([
    ['top', { top: '20px' }],
    ['mid', { top: '50%', transform: 'translateX(-50%) translateY(-50%)' }],
    ['bottom', { bottom: '0' }],
  ])('raises a figure named %s to its level', (level, style) => {
    const hints = { media_y: level } as StagingHints
    expect(figureStyle(image('a', 'staged_im', hints), 0, extent)).toMatchObject(style)
  })

  it('stations unplaced dialog figures by arrival, as pygame does', () => {
    const slots = [0, 1, 2, 3].map((index) => figureStyle(image('a', 'dialog_im'), index, extent))
    expect(slots.map((style) => style.left ?? `right ${style.right}`)).toEqual([
      '20px',
      'right 20px',
      '50%',
      '50%',
    ])
  })

  it('mirrors a flipped figure after placing it', () => {
    const hints = { media_x: 'left', media_flip_h: true } as StagingHints
    expect(figureStyle(image('a', 'dialog_im', hints), 0, extent).transform).toBe('scaleX(-1)')
  })
})

describe('castStage', () => {
  it('keeps the last backdrop and caps figures in arrival order', () => {
    const figures = Array.from({ length: STAGED_LIMIT + 3 }, (_, index) =>
      image(`fig-${index}`, 'staged_im')
    )
    const cast = castStage(
      [image('old', 'narrative_im'), ...figures, image('new', 'narrative_im')],
      {}
    )

    expect(cast.backdrop?.uid).toBe('new')
    expect(cast.figures.map(({ figure }) => figure.uid)).toEqual(
      figures.slice(0, STAGED_LIMIT).map((figure) => figure.uid)
    )
  })

  it('hides bound media before the cap, keeping hidden figures in the arrival count', () => {
    const decor = { media_visibility: { preference_id: 'decor', values: [true] } }
    const hidden = image('hidden', 'dialog_im', decor)
    const crowd = Array.from({ length: STAGED_LIMIT }, (_, index) =>
      image(`fig-${index}`, 'staged_im')
    )
    const cast = castStage(
      [image('bg', 'narrative_im', decor), hidden, image('shown', 'dialog_im'), ...crowd],
      { decor: false }
    )

    expect(cast.backdrop).toBeUndefined()
    expect(cast.figures).toHaveLength(STAGED_LIMIT)
    expect(cast.figures[0]).toEqual({ figure: expect.objectContaining({ uid: 'shown' }), index: 1 })
  })
})

describe('isStagedMedia', () => {
  it('stages drawable backdrops and figures only', () => {
    expect(isStagedMedia(image('bg', 'narrative_im'))).toBe(true)
    expect(isStagedMedia(image('fig', 'staged_im'))).toBe(true)
    expect(isStagedMedia(image('face', 'dialog_im'))).toBe(true)
    expect(isStagedMedia(image('plate', 'map_im'))).toBe(false)
    expect(isStagedMedia(image('face', 'avatar_im'))).toBe(false)
    expect(isStagedMedia({ ...image('face', 'dialog_im'), url: '' })).toBe(false)
    expect(isStagedMedia({ ...image('bark', 'dialog_im'), media_type: 'audio' })).toBe(false)
  })
})

describe('foldStage', () => {
  const room = [image('bg', 'narrative_im'), image('clerk', 'dialog_im')]

  it('replaces the stage with a step that states the room', () => {
    const backdrop = [image('bg2', 'narrative_im')]
    const crowd = [image('crowd', 'staged_im')]
    expect(foldStage(room, backdrop)).toEqual(backdrop)
    expect(foldStage(room, crowd)).toEqual(crowd)
  })

  it('keeps the stage through a step that states nothing', () => {
    expect(foldStage(room, [])).toEqual(room)
  })

  it('adds the figures of a step that states no room', () => {
    const face = image('face', 'dialog_im')
    expect(foldStage(room, [face])).toEqual([...room, face])
  })
})

describe('foldSteps', () => {
  it('folds one envelope at its journal steps, so a later room replaces an earlier one', () => {
    const court = [image('court', 'narrative_im', {}, 2), image('clerk', 'dialog_im', {}, 2)]
    const yard = [image('yard', 'narrative_im', {}, 4), image('worker', 'dialog_im', {}, 4)]
    expect(foldSteps([...court, ...yard])).toEqual(yard)
  })

  it('keeps the room through steps that bring only figures', () => {
    const court = [image('court', 'narrative_im', {}, 2), image('clerk', 'dialog_im', {}, 2)]
    const face = image('face', 'dialog_im', {}, 3)
    expect(foldSteps([...court, face])).toEqual([...court, face])
  })
})
