import type {
  JournalAction,
  JournalStoryUpdate,
  WorldInfo,
  WorldList,
} from '@/types'

export const mockBlock1: JournalStoryUpdate = {
  uid: 'block1_uid',
  text: 'Lorem ipsum dolor sit amet...',
  dialog: [
    {
      uid: 'dialog-1',
      text: 'Lorem ipsum dolor sit amet...',
    },
    {
      uid: 'dialog-2',
      text: 'sed do eiusmod tempor...',
      style_dict: { color: 'rgb(var(--v-theme-primary))', opacity: 0.9 },
      media: [
        {
          media_role: 'avatar_im',
          url: '/media/avatar.png',
          orientation: 'square',
        },
      ],
    },
  ],
  media: [
    {
      media_role: 'narrative_im',
      url: 'https://picsum.photos/1200/400',
      orientation: 'landscape',
    },
  ],
  actions: [
    {
      uid: 'action-1',
      text: 'Explore the area',
    },
  ],
}

export const mockBlock2: JournalStoryUpdate = {
  uid: 'block2_uid',
  text: 'Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris...',
  media: [
    {
      media_role: 'avatar_im',
      url: 'https://picsum.photos/400/400',
      orientation: 'portrait',
    },
  ],
  actions: [
    {
      uid: 'action-2',
      text: 'Respond to the call',
    },
  ],
}

export const mockWorldList: WorldList = [
  { key: 'tangl_world', value: 'Tangl World' },
  { key: 'solarpunk', value: 'Solarpunk Stories' },
]

export const mockWorldInfo: WorldInfo = {
  world_id: 'tangl_world',
  title: 'My world!',
  author: ['StoryTangl Team'],
  date: '2025-01-01',
  version: '2.7.9',
  summary: 'A cozy corner of the Tangl multiverse used for development tests.',
  media: [
    {
      media_role: 'cover_im',
      url: 'https://picsum.photos/800/320',
      orientation: 'landscape',
    },
  ],
}

export const mockActions: JournalAction[] = [
  {
    uid: 'mock-action-1',
    text: 'Take the left path',
  },
  {
    uid: 'mock-action-2',
    text: 'Take the right path',
  },
]

export const mockUserSecretResponse = {
  secret: 'dev-secret-123',
  api_key: 'mock-api-key-123',
}

export const mockUpdatedSecretResponse = {
  secret: 'updated-secret-456',
  api_key: 'updated-api-key-456',
}

export const mockStatus = [
  {
    key: 'status',
    value: 'working',
    style: { color: 'red' },
  },
  {
    key: 'health',
    value: '100/100',
    style: { color: 'green' },
    icon: 'heart',
  },
  {
    key: 'location',
    value: 'Dark Forest',
    icon: 'map-marker',
  },
  {
    key: 'unstyled',
    value: 'plain text',
  },
]

export const mockSystemInfo = {
  version: '3.7.0',
  uptime: '72h',
  status: 'operational',
}
