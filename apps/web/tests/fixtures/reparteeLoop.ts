import type { ProjectedState } from '@/types'

/**
 * World info for `repartee_loop`, as the real REST app serves it: the bare
 * catalog advertises its channels, and `?channels=ui-preferences` returns the
 * declarations from `worlds/repartee_loop/world.yaml`.
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

export const reparteePreferencesInfo: ProjectedState = {
  channels: [],
  sections: [
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
