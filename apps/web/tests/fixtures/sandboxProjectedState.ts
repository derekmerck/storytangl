import type { InfoAffordance, InfoState, ProjectedState } from '@/types'

export const sandboxInfoAffordances: InfoAffordance[] = [
  {
    channel_id: 'ui-world-time',
    label: 'Watch',
    shortcuts: ['t', 'time'],
  },
  {
    channel_id: 'ui-location',
    label: 'Here',
    shortcuts: ['h', 'look'],
  },
  {
    channel_id: 'ui-inventory',
    label: 'Carrying',
    shortcuts: ['i', 'inv'],
  },
  {
    channel_id: 'ui-map',
    label: 'Map',
    shortcuts: ['m', 'map'],
  },
  {
    channel_id: 'ui-agenda',
    label: 'Schedule',
    shortcuts: ['a'],
  },
  {
    channel_id: 'ui-objectives',
    label: 'Objectives',
    shortcuts: ['o'],
  },
  {
    channel_id: 'ui-help',
    label: 'Help',
    shortcuts: ['?'],
  },
]

export const sandboxInfoState: InfoState = {
  version: 17,
  dirty_kinds: ['ui-location', 'ui-inventory', 'ui-agenda'],
  available_kinds: [
    'ui-sidebar',
    'ui-inventory',
    'ui-map',
    'ui-world-time',
    'ui-agenda',
    'ui-location',
    'ui-objectives',
    'ui-help',
  ],
}

export const sandboxProjectedState: ProjectedState = {
  channels: sandboxInfoAffordances,
  sections: [
    {
      section_id: 'world_time',
      title: 'Time',
      kind: 'world_time',
      value: {
        value_type: 'kv_list',
        items: [
          { key: 'day', value: 3 },
          { key: 'period', value: 'evening' },
        ],
      },
    },
    {
      section_id: 'location',
      title: 'Here',
      kind: 'location',
      value: {
        value_type: 'item_list',
        items: [
          { label: 'Bedroom', detail: 'north wing', tags: ['place'] },
          { label: 'brass lamp', detail: 'on the desk', tags: ['fixture', 'takeable'] },
        ],
      },
    },
    {
      section_id: 'agenda',
      title: 'Schedule',
      kind: 'agenda',
      value: {
        value_type: 'item_list',
        items: [
          { label: 'Guard changes watch', detail: 'evening', tags: ['known'] },
        ],
      },
    },
  ],
}
