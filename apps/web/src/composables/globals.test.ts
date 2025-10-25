import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'

import type { JournalMediaItems } from '@/types'

import { makeMediaDict, remapURL, useGlobal } from './globals'

const DEFAULT_API_URL = 'http://localhost:8000/api/v2'

beforeEach(() => {
  vi.unstubAllEnvs()
  vi.stubEnv('VITE_DEFAULT_API_URL', DEFAULT_API_URL)
  vi.stubEnv('VITE_DEBUG', 'false')
  vi.stubEnv('VITE_VERBOSE', 'false')
})

afterEach(() => {
  vi.unstubAllEnvs()
})

describe('remapURL', () => {
  it('converts relative URL to absolute using API base', () => {
    const result = remapURL('/media/image.png')
    expect(result).toBe('http://localhost:8000/media/image.png')
  })

  it('leaves absolute URLs unchanged', () => {
    const url = 'https://example.com/image.jpg'
    expect(remapURL(url)).toBe(url)
  })

  it('handles URLs without leading slash', () => {
    const result = remapURL('media/image.png')
    expect(result).toBe('http://localhost:8000/media/image.png')
  })
})

describe('makeMediaDict', () => {
  it('transforms media array to dictionary by role', () => {
    const mediaItems: JournalMediaItems = [
      { media_role: 'narrative_im', url: '/img1.png', orientation: 'landscape' },
      { media_role: 'avatar_im', url: '/img2.png' },
    ]
    const block = { media: mediaItems }

    const dict = makeMediaDict(block)

    expect(dict).toHaveProperty('narrative_im')
    expect(dict.narrative_im?.url).toBe('http://localhost:8000/img1.png')
    expect(dict.narrative_im?.orientation).toBe('landscape')
    expect(dict).toHaveProperty('avatar_im')
  })

  it('returns empty object for blocks without media', () => {
    const block = { text: 'No media' }
    const dict = makeMediaDict(block)
    expect(dict).toEqual({})
  })

  it('handles empty media array', () => {
    const block = { media: [] as JournalMediaItems }
    const dict = makeMediaDict(block)
    expect(dict).toEqual({})
  })
})

describe('useGlobal', () => {
  it('exports $http axios instance', () => {
    const { $http } = useGlobal()
    expect($http.value).toBeDefined()
    expect(typeof $http.value.get).toBe('function')
  })

  it('exports debug flags from environment', () => {
    const { $debug, $verbose } = useGlobal()
    expect(typeof $debug.value).toBe('boolean')
    expect(typeof $verbose.value).toBe('boolean')
  })
})

describe('axios configuration', () => {
  it('sets base URL from environment', () => {
    const { $http } = useGlobal()
    expect($http.value.defaults.baseURL).toBe(DEFAULT_API_URL)
  })

  it('includes Content-Type header', () => {
    const { $http } = useGlobal()
    const header = ($http.value.defaults.headers.common as Record<string, string>)[
      'Content-Type'
    ]
    expect(header).toBe('application/json')
  })

  it('can make successful GET request', async () => {
    const { $http } = useGlobal()
    const response = await $http.value.get('/story/update')
    expect(response.status).toBe(200)
    expect(Array.isArray(response.data)).toBe(true)
  })
})
