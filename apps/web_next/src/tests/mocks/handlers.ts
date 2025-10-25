import { http, HttpResponse } from 'msw'

import {
  mockActions,
  mockBlock1,
  mockBlock2,
  mockUpdatedSecretResponse,
  mockUserSecretResponse,
  mockWorldInfo,
  mockWorldList,
} from './mockData'

const apiBase = (import.meta.env?.VITE_DEFAULT_API_URL ?? 'http://localhost:8000/api/v2').replace(
  /\/$/,
  '',
)

type UserWorldRequest = { uid?: string }
type UserSecretRequest = { secret?: string }

export const handlers = [
  http.get(`${apiBase}/story/update`, () => {
    return HttpResponse.json([mockBlock1, mockBlock2])
  }),

  http.post(`${apiBase}/story/do`, async ({ request }) => {
    const body = await request.json()
    console.debug('Mock story/do called with:', body)
    return HttpResponse.json([mockBlock1])
  }),

  http.get(`${apiBase}/story/actions`, () => {
    return HttpResponse.json(mockActions)
  }),

  http.get(`${apiBase}/system/worlds`, () => {
    return HttpResponse.json(mockWorldList)
  }),

  http.get(`${apiBase}/world/:worldId/info`, ({ params }) => {
    return HttpResponse.json({
      ...mockWorldInfo,
      world_id: params.worldId as string,
    })
  }),

  http.put(`${apiBase}/user/world`, async ({ request }) => {
    const body = (await request.json()) as UserWorldRequest | null
    return HttpResponse.json({ uid: body?.uid ?? 'tangl_world' })
  }),

  http.get(`${apiBase}/system/secret`, () => {
    return HttpResponse.json(mockUserSecretResponse)
  }),

  http.put(`${apiBase}/user/secret`, async ({ request }) => {
    const body = (await request.json()) as UserSecretRequest | null
    return HttpResponse.json({
      ...mockUpdatedSecretResponse,
      secret: body?.secret ?? mockUpdatedSecretResponse.secret,
    })
  }),
]
