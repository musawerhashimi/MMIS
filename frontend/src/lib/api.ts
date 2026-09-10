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

/**
 * Where the session is kept.
 *
 * sessionStorage rather than localStorage, so each browser tab holds its own
 * login. A supervisor and a student can be signed in side by side, which is
 * how staff actually work when helping someone, and how the system gets
 * tested at all.
 *
 * The cost is that closing a tab ends that tab's session. That is the right
 * trade on shared university computers, where the next person to sit down
 * should not inherit whoever was there before.
 *
 * Some browsers throw on access in private mode, so every call is guarded
 * and the app falls back to being signed out rather than failing to load.
 */
function read(key: string): string | null {
  try {
    return sessionStorage.getItem(key)
  } catch {
    return null
  }
}

function write(key: string, value: string): void {
  try {
    sessionStorage.setItem(key, value)
  } catch {
    // Nothing to do — the person stays signed in for this page only.
  }
}

function remove(key: string): void {
  try {
    sessionStorage.removeItem(key)
  } catch {
    // Already gone as far as this tab is concerned.
  }
}

export const tokens = {
  get access() {
    return read(ACCESS_KEY)
  },
  get refresh() {
    return read(REFRESH_KEY)
  },
  set(access: string, refresh?: string) {
    write(ACCESS_KEY, access)
    if (refresh) write(REFRESH_KEY, refresh)
  },
  clear() {
    remove(ACCESS_KEY)
    remove(REFRESH_KEY)
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
