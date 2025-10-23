import type { 
  JournalStoryUpdate,
  StoryStatus,
  SystemStatus,
  WorldInfo,
  UserInfo,
} from '@/types'

export const mockStoryUpdate: JournalStoryUpdate[] = [
  {
    uid: 'block-1',
    text: '<p>You wake up in a dimly lit room. The air is thick with dust and the smell of old paper.</p>',
    media: [
      {
        media_role: 'narrative_im',
        url: '/media/images/room.png',
      },
    ],
    actions: [
      {
        uid: 'action-1',
        text: 'Look around',
        icon: 'eye',
      },
      {
        uid: 'action-2',
        text: 'Try the door',
        icon: 'door-open',
      },
    ],
  },
]

export const mockStoryStatus: StoryStatus = [
  {
    key: 'Location',
    value: 'Dusty Room',
    icon: 'map-marker',
  },
  {
    key: 'Health',
    value: '100',
    icon: 'heart',
  },
  {
    key: 'Items',
    value: '3',
    icon: 'backpack',
  },
]

export const mockSystemInfo: SystemStatus = {
  engine: 'StoryTangl',
  version: '3.7.0',
  uptime: '2 hours',
  worlds: 5,
  users: 42,
  media: [
    {
      media_role: 'info_im',
      url: '/media/system/logo.png',
    },
  ],
}

export const mockWorldInfo: WorldInfo = {
  world_id: 'test-world',
  version: '1.0.0',
  title: 'Test Adventure',
  author: 'Test Author',
  date: '2025-01-01',
  comments: 'A test world for development',
  media: [
    {
      media_role: 'info_im',
      url: '/media/worlds/test-world/cover.png',
    },
  ],
}

export const mockUserInfo: UserInfo = {
  user_id: 'test-user-123',
  user_secret: 'test-secret',
  created_dt: '2025-01-01T00:00:00Z',
  last_played_dt: '2025-01-15T12:00:00Z',
  worlds_played: ['test-world', 'another-world'],
  stories_finished: 3,
  turns_played: 150,
  achievements: ['first-steps', 'explorer'],
}

// Helper to create mock story updates with different content
export function createMockStoryUpdate(overrides?: Partial<JournalStoryUpdate>): JournalStoryUpdate {
  return {
    uid: `block-${Math.random()}`,
    text: '<p>Default story text</p>',
    actions: [],
    ...overrides,
  }
}
