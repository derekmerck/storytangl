import type { MediaStoryFragment, ProjectedState, RuntimeEnvelope, StoryFragment } from '@/types'

/**
 * World info for `repartee_loop`, as the real REST app serves it: the bare
 * catalog advertises its channels, and `?channels=ui-stage,ui-preferences`
 * returns the stage and preference declarations from its `world.yaml`.
 */
export const reparteeWorldCatalog: ProjectedState = {
  channels: [
    { channel_id: 'ui-style-hints-html', label: 'HTML style hints', shortcuts: [] },
    { channel_id: 'ui-branding', label: 'Branding', shortcuts: [] },
    { channel_id: 'ui-stage', label: 'Stage extent', shortcuts: [] },
    { channel_id: 'ui-preferences', label: 'Preferences', shortcuts: [] },
  ],
  sections: [],
}

export const reparteePresentationInfo: ProjectedState = {
  channels: [],
  sections: [
    {
      section_id: 'ui-stage',
      title: 'Stage extent',
      kind: 'stage_extent',
      value: { value_type: 'stage_extent', width: 320, height: 200 },
      hints: null,
    },
    {
      section_id: 'ui-preferences',
      title: 'Preferences',
      kind: 'ui_preferences',
      value: {
        value_type: 'ui_preferences',
        preferences: [
          {
            id: 'sprites-visible',
            label: 'Decorative sprites',
            kind: 'boolean',
            default: true,
            help: 'Show optional staged character art.',
            shortcut: 'F1',
          },
          {
            id: 'clerk-motion',
            kind: 'enum',
            values: ['idle', 'call', 'response'],
            default: 'idle',
            label: 'Clerk motion',
            help: "Choose the clerk's local sprite pose.",
            shortcut: 'F2',
          },
        ],
      },
      hints: null,
    },
  ],
}

const metadata = { world_id: 'repartee_loop', ledger_id: 'repartee-ledger' }
const image = (uid: string, role: string, file: string, staging_hints = {}): MediaStoryFragment => ({
  uid,
  fragment_type: 'media',
  media_role: role,
  text: null,
  scope: 'world',
  media_type: 'image',
  content_format: 'url',
  staging_hints,
  url: `/media/world/repartee_loop/images/${file}`,
})

/** The clerk as `repartee_loop` stages it, hints exactly as the service sends them. */
export const reparteeClerk = image('clerk', 'dialog_im', 'clerk_sprite.png', {
  media_transition: 'from_left',
  media_timing: 'loop',
  media_visibility: { preference_id: 'sprites-visible', values: [true] },
  media_x: 'left',
  media_y: 'bottom',
  media_flip_h: true,
  media_clip: 'idle',
  media_clip_binding: {
    axes: ['clerk-motion'],
    rows: [
      { values: ['idle'], clip: 'idle' },
      { values: ['call'], clip: 'call' },
      { values: ['response'], clip: 'response' },
    ],
  },
})

/** One step's envelope; the service stamps each fragment with its journal step. */
const played = (step: number, fragments: StoryFragment[]): RuntimeEnvelope => ({
  step,
  metadata,
  fragments: fragments.map((fragment) => ({ ...fragment, step })),
})

/** Its first four steps: the quay, the clerk on the quay, the map plate alone, the yard. */
export const reparteeSteps: RuntimeEnvelope[] = [
  played(1, [
    { uid: 'quay-text', fragment_type: 'content', content: 'At the quay, every introduction is also a challenge.' },
    image('quay-bg', 'narrative_im', 'quai_bg.png', { media_shape: 'landscape' }),
    { uid: 'quay-go', fragment_type: 'choice', edge_id: 'quay-edge', text: 'Step into the practice court' },
  ]),
  played(2, [
    { uid: 'court-text', fragment_type: 'content', content: 'The clerk hands you one opening line.' },
    image('court-bg', 'narrative_im', 'quai_bg.png', { media_shape: 'landscape' }),
    reparteeClerk,
    { uid: 'court-go', fragment_type: 'choice', edge_id: 'court-edge', text: 'Step out onto the quay' },
  ]),
  played(3, [
    { uid: 'map-text', fragment_type: 'content', content: 'The district runs from the water to the salon steps.' },
    image('map', 'map_im', 'quay_map.png'),
    { uid: 'map-go', fragment_type: 'choice', edge_id: 'map-edge', text: 'Go to The Practice Yard' },
  ]),
  played(4, [
    { uid: 'yard-text', fragment_type: 'content', content: 'The worker looks up from the crates.' },
    image('yard-bg', 'narrative_im', 'warehouse_bg.png', { media_shape: 'landscape' }),
    image('worker', 'dialog_im', 'worker_sprite.png', { media_x: 'right', media_y: 'bottom' }),
    { uid: 'yard-go', fragment_type: 'choice', edge_id: 'yard-edge', text: 'Back to the quay' },
  ]),
]
