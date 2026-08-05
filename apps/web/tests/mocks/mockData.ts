import type { WorldInfo, WorldList } from '@/types'

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

export const mockUserSecretResponse = {
  user_secret: 'dev-secret-123',
  api_key: 'mock-api-key-123',
}

export const mockUpdatedSecretResponse = {
  user_secret: 'updated-secret-456',
  api_key: 'updated-api-key-456',
}

export const mockUserInfo = {
  user_id: 'test-user-id',
  user_secret: 'dev-secret-123',
  created_dt: '2026-01-01T00:00:00Z',
  last_played_dt: '2026-01-01T00:00:00Z',
  worlds_played: [],
  stories_finished: 0,
  turns_played: 0,
}

export const mockSystemInfo = {
  version: '3.8',
  uptime: '72h',
  status: 'operational',
}
