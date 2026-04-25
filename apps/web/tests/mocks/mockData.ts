import type {
  JournalAction,
  WorldInfo,
  WorldList,
} from '@/types'

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

export const mockSystemInfo = {
  version: '3.7.0',
  uptime: '72h',
  status: 'operational',
}
