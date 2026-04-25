import { http, HttpResponse } from 'msw'

import {
  crossroadsNextRuntimeEnvelope,
  crossroadsProjectedState,
  crossroadsRuntimeEnvelope,
} from '@tests/fixtures'
import {
  mockActions,
  mockSystemInfo,
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
type StoryDoRequest = { choice_id?: unknown; payload?: unknown }

export const handlers = [
  http.get(`${apiBase}/story/update`, () => {
    return HttpResponse.json(crossroadsRuntimeEnvelope)
  }),

  http.post(`${apiBase}/story/do`, async ({ request }) => {
    const body = (await request.json()) as StoryDoRequest | null
    if (typeof body?.choice_id !== 'string') {
      return HttpResponse.json(
        { error: 'story action payload requires choice_id' },
        { status: 400 },
      )
    }
    return HttpResponse.json(crossroadsNextRuntimeEnvelope)
  }),

  http.get(`${apiBase}/story/actions`, () => {
    return HttpResponse.json(mockActions)
  }),

  http.get(`${apiBase}/system/worlds`, () => {
    return HttpResponse.json(mockWorldList)
  }),

  http.get(`${apiBase}/story/info`, () => {
    return HttpResponse.json(crossroadsProjectedState)
  }),

  http.get(`${apiBase}/world/:worldId/info`, ({ params }) => {
    return HttpResponse.json({
      ...mockWorldInfo,
      world_id: params.worldId as string,
    })
  }),

  http.get(`${apiBase}/system/info`, () => {
    return HttpResponse.json(mockSystemInfo)
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
