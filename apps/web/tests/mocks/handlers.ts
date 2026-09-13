import { http, HttpResponse } from 'msw'

import {
  crossroadsNextRuntimeEnvelope,
  crossroadsProjectedState,
  crossroadsRuntimeEnvelope,
} from '@tests/fixtures'
import {
  mockSystemInfo,
  mockUpdatedSecretResponse,
  mockUserInfo,
  mockUserSecretResponse,
  mockWorldInfo,
  mockWorldList,
} from './mockData'

const apiBase = (import.meta.env?.VITE_DEFAULT_API_URL ?? 'http://localhost:8000/api/v2').replace(
  /\/$/,
  '',
)

type UserWorldRequest = { uid?: string }
type StoryDoRequest = {
  edge_id?: unknown
  find_edge?: { kind?: unknown; command?: unknown }
  payload?: unknown
}

export const handlers = [
  http.get(`${apiBase}/story/update`, () => {
    return HttpResponse.json(crossroadsRuntimeEnvelope)
  }),

  http.post(`${apiBase}/story/do`, async ({ request }) => {
    const body = (await request.json()) as StoryDoRequest | null
    const direct = typeof body?.edge_id === 'string'
    const command =
      body?.find_edge?.kind === 'command' && typeof body.find_edge.command === 'string'
    if (!direct && !command) {
      return HttpResponse.json(
        { error: 'story action payload requires edge_id or find_edge' },
        { status: 400 },
      )
    }
    return HttpResponse.json(crossroadsNextRuntimeEnvelope)
  }),

  http.get(`${apiBase}/system/worlds`, () => {
    return HttpResponse.json(mockWorldList)
  }),

  http.get(`${apiBase}/story/info`, () => {
    return HttpResponse.json(crossroadsProjectedState)
  }),

  http.get(`${apiBase}/world/:worldId/info`, ({ request }) => {
    const worldId = new URL(request.url).pathname.split('/').at(-2) ?? 'world'
    return HttpResponse.json({
      channels: [],
      sections: [
        {
          section_id: 'ui-branding',
          title: 'Branding',
          kind: 'branding',
          value: {
            value_type: 'branding',
            name: worldId === 'tangl_world' ? mockWorldInfo.title : worldId,
            logo_media: 'cover_im',
          },
        },
      ],
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

  http.get(`${apiBase}/user/info`, () => {
    return HttpResponse.json(mockUserInfo)
  }),

  http.post(`${apiBase}/user/create`, ({ request }) => {
    const secret = new URL(request.url).searchParams.get('secret')
    return HttpResponse.json({
      ...mockUserSecretResponse,
      user_secret: secret ?? mockUserSecretResponse.user_secret,
    })
  }),

  http.put(`${apiBase}/user/secret`, ({ request }) => {
    const secret = new URL(request.url).searchParams.get('secret')
    if (!secret || request.headers.get('X-Api-Key') !== mockUserSecretResponse.api_key) {
      return HttpResponse.json({ detail: 'Invalid secret rotation request' }, { status: 400 })
    }
    return HttpResponse.json({
      ...mockUpdatedSecretResponse,
      user_secret: secret,
    })
  }),
]
