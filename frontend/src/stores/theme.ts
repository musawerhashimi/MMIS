/** Light or dark, remembered between visits. */
import { create } from 'zustand'

type Theme = 'light' | 'dark'
const KEY = 'mms.theme'

/**
 * The chosen theme stays in localStorage, unlike the session.
 *
 * A person's preference for light or dark should follow them across tabs and
 * survive closing the browser; who they are signed in as should not. Some
 * browsers throw on storage access in private mode, so both calls are
 * guarded and fall back to the device setting.
 */
function remember(theme: Theme): void {
  try {
    localStorage.setItem(KEY, theme)
  } catch {
    // The choice applies to this session only. Not worth interrupting anyone.
  }
}

function initial(): Theme {
  try {
    const stored = localStorage.getItem(KEY) as Theme | null
    if (stored === 'light' || stored === 'dark') return stored
  } catch {
    // Fall through to the device setting.
  }
  // Rather than forcing a bright screen on someone reading at night.
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
      remember(next)
      apply(next)
      set({ theme: next })
    },
    set(next) {
      remember(next)
      apply(next)
      set({ theme: next })
    },
  }
})
