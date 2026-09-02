/**
 * The HTTP client.
 *
 * Two things happen here that the rest of the app then never worries about:
 * an expired access token is refreshed and the request retried, and every
 * error is unwrapped into a plain message the UI can show.
 */
import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import type { ApiError } from '@/types'

const ACCESS_KEY = 'mms.access'
const REFRESH_KEY = 'mms.refresh'

export const tokens = {
  get access() {
    return localStorage.getItem(ACCESS_KEY)
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY)
  },
  set(access: string, refresh?: string) {
    localStorage.setItem(ACCESS_KEY, access)
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
  },
}

export const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = tokens.access
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

/**
 * While a refresh is in flight, other failed requests wait for it rather than
 * each firing their own refresh — otherwise one expired token becomes a burst
 * of identical calls.
 */
let refreshing: Promise<string | null> | null = null

async function refreshAccessToken(): Promise<string | null> {
  const refresh = tokens.refresh
  if (!refresh) return null

  try {
    const { data } = await axios.post('/api/v1/auth/refresh/', { refresh })
    tokens.set(data.access, data.refresh)
    return data.access as string
  } catch {
    tokens.clear()
    return null
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiError>) => {
    const original = error.config as InternalAxiosRequestConfig & { _retried?: boolean }

    if (error.response?.status === 401 && original && !original._retried) {
      original._retried = true

      refreshing ??= refreshAccessToken().finally(() => {
        refreshing = null
      })
      const token = await refreshing

      if (token) {
        original.headers.Authorization = `Bearer ${token}`
        return api(original)
      }

      // The session is genuinely over. Send them to sign in again, keeping
      // where they were so they land back on it.
      const here = window.location.pathname + window.location.search
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = `/login?next=${encodeURIComponent(here)}`
      }
    }

    return Promise.reject(error)
  },
)

/** Turn any thrown error into something worth showing a person. */
export function errorMessage(error: unknown): string {
  if (axios.isAxiosError<ApiError>(error)) {
    const payload = error.response?.data
    if (payload?.error?.message) return payload.error.message
    if (error.code === 'ERR_NETWORK') {
      return 'Cannot reach the server. Check your connection.'
    }
  }
  if (error instanceof Error) return error.message
  return 'Something went wrong.'
}

/** Field-level errors, for showing beside the input that caused them. */
export function fieldErrors(error: unknown): Record<string, string> {
  if (!axios.isAxiosError<ApiError>(error)) return {}
  const details = error.response?.data?.error?.details ?? {}
  const flat: Record<string, string> = {}
  for (const [field, value] of Object.entries(details)) {
    flat[field] = Array.isArray(value) ? value[0] : String(value)
  }
  return flat
}
