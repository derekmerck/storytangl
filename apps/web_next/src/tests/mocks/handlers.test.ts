import axios from 'axios'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const DEFAULT_API_URL = 'http://localhost:8000/api/v2'

beforeEach(() => {
  vi.stubEnv('VITE_DEFAULT_API_URL', DEFAULT_API_URL)
  axios.defaults.baseURL = DEFAULT_API_URL
})

afterEach(() => {
  vi.unstubAllEnvs()
})

describe('MSW Handlers', () => {
  it('returns story blocks on /story/update', async () => {
    const response = await axios.get('/story/update')
    expect(Array.isArray(response.data)).toBe(true)
    expect(response.data[0]).toHaveProperty('uid')
    expect(response.data[0]).toHaveProperty('text')
  })

  it('returns blocks on /story/do', async () => {
    const response = await axios.post('/story/do', {
      uid: 'action_uid',
      passback: null,
    })
    expect(Array.isArray(response.data)).toBe(true)
    expect(response.data[0]).toHaveProperty('uid')
  })

  it('returns world list on /system/worlds', async () => {
    const response = await axios.get('/system/worlds')
    expect(Array.isArray(response.data)).toBe(true)
    expect(response.data[0]).toHaveProperty('key')
  })

  it('returns status entries on /story/status', async () => {
    const response = await axios.get('/story/status')
    expect(Array.isArray(response.data)).toBe(true)
    expect(response.data[0]).toHaveProperty('key')
    expect(response.data[0]).toHaveProperty('value')
  })

  it('returns system info on /system/info', async () => {
    const response = await axios.get('/system/info')
    expect(response.data).toHaveProperty('status')
  })
})
