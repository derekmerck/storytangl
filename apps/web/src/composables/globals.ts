import axios, { type AxiosInstance } from 'axios'
import { ref, type Ref } from 'vue'

import type { JournalMediaDict, JournalMediaItems, MediaRole } from '@/types'

const DEFAULT_API_URL = 'http://localhost:8000/api/v2'

const resolveApiBase = (): string => {
  const envUrl = import.meta.env?.VITE_DEFAULT_API_URL
  return envUrl?.length ? envUrl : DEFAULT_API_URL
}

const toBoolean = (value: string | undefined): boolean => value === 'true'

const normalisePath = (url: string): string => {
  if (!url.startsWith('/')) {
    return `/${url}`
  }
  return url
}

/**
 * Remaps relative URLs to absolute URLs using the API base URL origin.
 *
 * @param url - The URL to remap (relative or absolute)
 * @returns The remapped absolute URL
 * @example
 * ```ts
 * remapURL('/media/image.png')
 * // returns 'http://localhost:8000/media/image.png'
 * ```
 */
export const remapURL = (url: string): string => {
  if (!url) {
    return url
  }

  if (/^https?:\/\//i.test(url)) {
    return url
  }

  try {
    const base = new URL(resolveApiBase())
    return `${base.origin}${normalisePath(url)}`
  } catch (error) {
    console.warn('Failed to remap URL, returning original value.', error)
    return url
  }
}

type MediaCarrier = {
  [key: string]: unknown
  media?: JournalMediaItems
}

/**
 * Transforms the media array on an object into a dictionary keyed by media role.
 *
 * The function returns a new dictionary without mutating the original media array.
 */
export const makeMediaDict = (
  obj: MediaCarrier,
  mediaKey: keyof MediaCarrier = 'media',
): JournalMediaDict => {
  const mediaValue = obj?.[mediaKey]

  if (!Array.isArray(mediaValue) || mediaValue.length === 0) {
    return {}
  }

  const dictionary: JournalMediaDict = {}
  const mediaArray = mediaValue as JournalMediaItems

  for (const item of mediaArray) {
    if (!item?.media_role) {
      continue
    }

    const role = item.media_role as MediaRole

    dictionary[role] = {
      ...item,
      url: item.url ? remapURL(item.url) : item.url,
    }
  }

  return dictionary
}

const createHttpClient = (
  $debug: Ref<boolean>,
  $verbose: Ref<boolean>,
): AxiosInstance => {
  const instance = axios.create({
    baseURL: resolveApiBase(),
    headers: {
      'Content-Type': 'application/json',
    },
  })

  instance.interceptors.request.use(
    (config) => {
      if ($debug.value) {
        const method = config.method?.toUpperCase() ?? 'GET'
        console.debug('API Request:', method, config.baseURL ?? '', config.url ?? '')
      }
      return config
    },
    (error) => {
      console.error('Request error:', error)
      return Promise.reject(error)
    },
  )

  instance.interceptors.response.use(
    (response) => {
      if ($verbose.value) {
        console.debug('API Response:', response.status, response.data)
      }
      return response
    },
    (error) => {
      console.error('Response error:', error)
      return Promise.reject(error)
    },
  )

  if (instance.defaults.headers.common) {
    ;(instance.defaults.headers.common as Record<string, string>)['Content-Type'] =
      'application/json'
  }

  return instance
}

const createGlobalState = () => {
  const $debug = ref(toBoolean(import.meta.env?.VITE_DEBUG))
  const $verbose = ref(toBoolean(import.meta.env?.VITE_VERBOSE))
  const $http = ref<AxiosInstance>(createHttpClient($debug, $verbose))

  return {
    $http,
    $debug,
    $verbose,
    remapURL,
    makeMediaDict,
  }
}

const globalState = createGlobalState()

/**
 * Provides access to global utilities shared across components.
 */
export const useGlobal = () => globalState
