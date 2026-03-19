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
  it('returns a runtime envelope on /story/update', async () => {
    const response = await axios.get('/story/update')
    expect(response.data).toHaveProperty('fragments')
    expect(Array.isArray(response.data.fragments)).toBe(true)
    expect(response.data.fragments[0]).toHaveProperty('uid')
    expect(response.data.fragments[0]).toHaveProperty('text')
  })

  it('returns a runtime envelope on /story/do', async () => {
    const response = await axios.post('/story/do', {
      uid: 'action_uid',
      passback: null,
    })
    expect(response.data).toHaveProperty('fragments')
    expect(Array.isArray(response.data.fragments)).toBe(true)
    expect(response.data.fragments[0]).toHaveProperty('uid')
  })

  it('returns world list on /system/worlds', async () => {
    const response = await axios.get('/system/worlds')
    expect(Array.isArray(response.data)).toBe(true)
    expect(response.data[0]).toHaveProperty('key')
  })

  it('returns projected state on /story/info', async () => {
    const response = await axios.get('/story/info')
    expect(response.data).toHaveProperty('sections')
    expect(Array.isArray(response.data.sections)).toBe(true)
    expect(response.data.sections[0]).toHaveProperty('title')
    expect(response.data.sections[0]).toHaveProperty('value')
    expect(response.data.sections[0]).toHaveProperty('value.value_type')
  })

  it('returns system info on /system/info', async () => {
    const response = await axios.get('/system/info')
    expect(response.data).toHaveProperty('status')
  })
})
