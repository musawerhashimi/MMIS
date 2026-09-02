/** Light or dark, remembered between visits. */
import { create } from 'zustand'

type Theme = 'light' | 'dark'
const KEY = 'mms.theme'

function initial(): Theme {
  const stored = localStorage.getItem(KEY) as Theme | null
  if (stored === 'light' || stored === 'dark') return stored
  // Fall back to whatever the device is already set to, rather than forcing
  // a bright screen on someone reading at night.
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function apply(theme: Theme) {
  document.documentElement.classList.toggle('dark', theme === 'dark')
  document.documentElement.style.colorScheme = theme
}

interface ThemeState {
  theme: Theme
  toggle: () => void
  set: (theme: Theme) => void
}

export const useTheme = create<ThemeState>((set, get) => {
  const theme = initial()
  apply(theme)

  return {
    theme,
    toggle() {
      const next = get().theme === 'dark' ? 'light' : 'dark'
      localStorage.setItem(KEY, next)
      apply(next)
      set({ theme: next })
    },
    set(next) {
      localStorage.setItem(KEY, next)
      apply(next)
      set({ theme: next })
    },
  }
})
