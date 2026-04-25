import type { ProjectedState } from '@/types'

export const crossroadsProjectedState: ProjectedState = {
  sections: [
    {
      section_id: 'health',
      title: 'Wounds',
      kind: 'status',
      value: { value_type: 'scalar', value: 'Sound' },
    },
    {
      section_id: 'purse',
      title: 'Purse',
      kind: 'resource',
      value: {
        value_type: 'kv_list',
        items: [
          { key: 'silver', value: 63 },
          { key: 'copper', value: 11 },
          { key: 'favors', value: 1 },
        ],
      },
    },
    {
      section_id: 'inventory',
      title: 'Satchel',
      kind: 'inventory',
      value: {
        value_type: 'item_list',
        items: [
          { label: 'Hooded lantern', detail: 'half-oil', tags: ['light'] },
          { label: 'Letter, sealed', detail: 'for Captain Ros', tags: ['quest'] },
          { label: "Elen's knife", detail: 'balanced', tags: ['weapon', 'borrowed'] },
        ],
      },
    },
    {
      section_id: 'party',
      title: 'Party',
      kind: 'roster',
      value: {
        value_type: 'table',
        columns: ['name', 'role', 'mood'],
        rows: [
          ['Bram', 'soldier', 'surly'],
          ['Elen', 'scout', 'watchful'],
        ],
      },
    },
    {
      section_id: 'tags',
      title: 'Conditions',
      kind: 'tags',
      value: { value_type: 'badges', items: ['rain-soaked', 'hungry', 'hunted'] },
    },
  ],
}
