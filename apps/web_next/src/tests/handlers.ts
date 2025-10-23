import { http, HttpResponse } from 'msw'
import { 
  mockStoryUpdate, 
  mockStoryStatus, 
  mockSystemInfo,
  mockWorldInfo,
  mockUserInfo 
} from './mockData'

const API_BASE = import.meta.env.VITE_DEFAULT_API_URL || 'http://localhost:8000/api/v2'

export const handlers = [
  // Story endpoints
  http.get(`${API_BASE}/story/update`, () => {
    return HttpResponse.json(mockStoryUpdate)
  }),

  http.post(`${API_BASE}/story/do`, async ({ request }) => {
    const body = await request.json()
    // In tests, we can validate the action format and return appropriate responses
    return HttpResponse.json(mockStoryUpdate)
  }),

  http.get(`${API_BASE}/story/status`, () => {
    return HttpResponse.json(mockStoryStatus)
  }),

  http.post(`${API_BASE}/story/story/create`, () => {
    return HttpResponse.json({ 
      story_id: 'test-story-123',
      message: 'Story created successfully' 
    })
  }),

  // System endpoints
  http.get(`${API_BASE}/system/info`, () => {
    return HttpResponse.json(mockSystemInfo)
  }),

  http.get(`${API_BASE}/system/worlds`, () => {
    return HttpResponse.json([
      { key: 'world1', value: 'Test World 1' },
      { key: 'world2', value: 'Test World 2' },
    ])
  }),

  // World endpoints
  http.get(`${API_BASE}/world/:worldId/info`, ({ params }) => {
    return HttpResponse.json({
      ...mockWorldInfo,
      world_id: params.worldId as string,
    })
  }),

  // User endpoints
  http.get(`${API_BASE}/user/info`, () => {
    return HttpResponse.json(mockUserInfo)
  }),

  http.post(`${API_BASE}/user/create`, () => {
    return HttpResponse.json({
      user_id: 'test-user-123',
      user_secret: 'test-secret',
      api_key: 'test-api-key',
    })
  }),

  http.put(`${API_BASE}/user/secret`, () => {
    return HttpResponse.json({
      user_id: 'test-user-123',
      user_secret: 'new-secret',
      api_key: 'new-api-key',
    })
  }),
]
