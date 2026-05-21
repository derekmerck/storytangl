import type { InfoAffordance, InfoState, ProjectedState } from '@/types'

export const sandboxInfoAffordances: InfoAffordance[] = [
  {
    kind: 'world_time',
    label: 'Watch',
    shortcuts: ['t', 'time'],
    query: { kinds: ['world_time'] },
  },
  {
    kind: 'presence',
    label: 'Here',
    shortcuts: ['h', 'look'],
    query: { kinds: ['location', 'presence'] },
  },
  {
    kind: 'inventory',
    label: 'Carrying',
    shortcuts: ['i', 'inv'],
    query: { kinds: ['inventory'] },
  },
  {
    kind: 'map',
    label: 'Map',
    shortcuts: ['m', 'map'],
    query: { type: 'map', format: 'graph' },
  },
  {
    kind: 'agenda',
    label: 'Schedule',
    shortcuts: ['a'],
    query: { kinds: ['agenda'] },
  },
  {
    kind: 'objectives',
    label: 'Objectives',
    shortcuts: ['o'],
    query: { kinds: ['objectives'] },
  },
  {
    kind: 'help',
    label: 'Help',
    shortcuts: ['?'],
    query: null,
  },
]

export const sandboxInfoState: InfoState = {
  version: 17,
  dirty_kinds: ['location', 'inventory', 'agenda'],
  available_kinds: [
    'status',
    'inventory',
    'map',
    'world_time',
    'agenda',
    'presence',
    'objectives',
    'help',
  ],
}

export const sandboxProjectedState: ProjectedState = {
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
