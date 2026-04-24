import { afterAll, afterEach, beforeAll } from 'vitest'
import type * as Msw from 'msw'
import type { SetupServerApi } from 'msw/node'

let activeServer: SetupServerApi | undefined
let activeHttp: typeof Msw.http | undefined
let activeHttpResponse: typeof Msw.HttpResponse | undefined

function installMemoryLocalStorage() {
  const store = new Map<string, string>()
  const storage: Storage = {
    get length() {
      return store.size
    },
    clear: () => store.clear(),
    getItem: (key: string) => store.get(String(key)) ?? null,
    key: (index: number) => Array.from(store.keys())[index] ?? null,
    removeItem: (key: string) => {
      store.delete(String(key))
    },
    setItem: (key: string, value: string) => {
      store.set(String(key), String(value))
    },
  }

  Object.defineProperty(globalThis, 'localStorage', {
    value: storage,
    configurable: true,
  })
  if (typeof window !== 'undefined') {
    Object.defineProperty(window, 'localStorage', {
      value: storage,
      configurable: true,
    })
  }
}

function getServer() {
  if (activeServer === undefined) {
    throw new Error('MSW server has not been initialized')
  }
  return activeServer
}

export const server = new Proxy({} as SetupServerApi, {
  get(_target, property: PropertyKey) {
    const realServer = getServer()
    const value = Reflect.get(realServer, property)
    return typeof value === 'function' ? value.bind(realServer) : value
  },
})

export const http = new Proxy({} as typeof Msw.http, {
  get(_target, property: PropertyKey) {
    if (activeHttp === undefined) {
      throw new Error('MSW http helpers have not been initialized')
    }
    const value = Reflect.get(activeHttp, property)
    return typeof value === 'function' ? value.bind(activeHttp) : value
  },
})

export const HttpResponse = new Proxy({} as typeof Msw.HttpResponse, {
  get(_target, property: PropertyKey) {
    if (activeHttpResponse === undefined) {
      throw new Error('MSW response helpers have not been initialized')
    }
    const value = Reflect.get(activeHttpResponse, property)
    return typeof value === 'function' ? value.bind(activeHttpResponse) : value
  },
})

beforeAll(async () => {
  installMemoryLocalStorage()
  const [
    { http: mswHttp, HttpResponse: mswHttpResponse },
    { setupServer },
    { handlers },
  ] = await Promise.all([import('msw'), import('msw/node'), import('./mocks/handlers')])
  activeHttp = mswHttp
  activeHttpResponse = mswHttpResponse
  activeServer = setupServer(...handlers)
  activeServer.listen({ onUnhandledRequest: 'error' })
})

afterEach(() => {
  globalThis.localStorage.clear()
  getServer().resetHandlers()
})

afterAll(() => {
  getServer().close()
  activeServer = undefined
  activeHttp = undefined
  activeHttpResponse = undefined
})
