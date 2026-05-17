import type { InfoAffordance, ProjectedState } from '@/types'

export const sandboxInfoAffordances: InfoAffordance[] = [
  {
    kind: 'map',
    label: 'Map',
    shortcuts: ['m', 'map'],
    query: { type: 'map', format: 'tiles' },
  },
  {
    kind: 'inventory',
    label: 'Inventory',
    shortcuts: ['i'],
  },
  {
    kind: 'party',
    label: 'Party',
    shortcuts: ['p'],
    query: { kinds: ['party', 'followers'] },
  },
]

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
