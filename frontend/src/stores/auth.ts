/** Who is signed in, and what they are allowed to see. */
import { create } from 'zustand'
import { api, tokens } from '@/lib/api'
import type { User } from '@/types'

interface AuthState {
  user: User | null
  loading: boolean
  initialised: boolean
  login: (username: string, password: string) => Promise<User>
  logout: () => void
  restore: () => Promise<void>
  refreshUser: () => Promise<void>
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  loading: false,
  initialised: false,

  async login(username, password) {
    set({ loading: true })
    try {
      const { data } = await api.post('/auth/login/', { username, password })
      tokens.set(data.access, data.refresh)
      set({ user: data.user, loading: false, initialised: true })
      return data.user as User
    } catch (error) {
      set({ loading: false })
      throw error
    }
  },

  logout() {
    tokens.clear()
    set({ user: null, initialised: true })
  },

  /**
   * Restore the session on a page reload.
   *
   * A stored token is not proof of a valid session — it may have expired
   * while the tab was closed — so the user is fetched rather than assumed.
   */
  async restore() {
    if (!tokens.access) {
      set({ initialised: true })
      return
    }
    try {
      const { data } = await api.get('/auth/me/')
      set({ user: data, initialised: true })
    } catch {
      tokens.clear()
      set({ user: null, initialised: true })
    }
  },

  async refreshUser() {
    const { data } = await api.get('/auth/me/')
    set({ user: data })
  },
}))
