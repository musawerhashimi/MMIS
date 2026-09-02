import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { LogOut, Menu, Moon, PanelLeftClose, PanelLeft, Sun, User as UserIcon } from 'lucide-react'
import { useAuth } from '@/stores/auth'
import { useTheme } from '@/stores/theme'
import { initials } from '@/lib/utils'
import { NotificationBell } from './NotificationBell'

interface Props {
  onToggleSidebar: () => void
  onOpenMobileNav: () => void
  collapsed: boolean
}

export function Topbar({ onToggleSidebar, onOpenMobileNav, collapsed }: Props) {
  const user = useAuth((s) => s.user)
  const logout = useAuth((s) => s.logout)
  const { theme, toggle } = useTheme()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)

  if (!user) return null

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b bg-[var(--surface-raised)] px-4">
      <div className="flex items-center gap-2">
        <button
          onClick={onOpenMobileNav}
          className="flex h-9 w-9 items-center justify-center rounded-lg text-[var(--text-muted)] hover:bg-[var(--surface-sunken)] md:hidden"
          aria-label="Open navigation"
        >
          <Menu className="h-4.5 w-4.5" />
        </button>
        <button
          onClick={onToggleSidebar}
          className="hidden h-9 w-9 items-center justify-center rounded-lg text-[var(--text-muted)] transition-colors hover:bg-[var(--surface-sunken)] hover:text-[var(--text)] md:flex"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <PanelLeft className="h-4.5 w-4.5" /> : <PanelLeftClose className="h-4.5 w-4.5" />}
        </button>
      </div>

      <div className="flex items-center gap-1">
        <button
          onClick={toggle}
          className="flex h-9 w-9 items-center justify-center rounded-lg text-[var(--text-muted)] transition-colors hover:bg-[var(--surface-sunken)] hover:text-[var(--text)]"
          aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
        >
          {theme === 'dark' ? <Sun className="h-4.5 w-4.5" /> : <Moon className="h-4.5 w-4.5" />}
        </button>

        <NotificationBell />

        <div className="relative">
          <button
            onClick={() => setMenuOpen((v) => !v)}
            onBlur={() => window.setTimeout(() => setMenuOpen(false), 150)}
            className="ml-1 flex items-center gap-2 rounded-lg py-1 pl-1 pr-2 transition-colors hover:bg-[var(--surface-sunken)]"
          >
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-brand-600 text-[11px] font-semibold text-white">
              {initials(user.full_name)}
            </span>
            <span className="hidden text-xs font-medium sm:block">{user.full_name}</span>
          </button>

          {menuOpen && (
            <div className="animate-in absolute right-0 top-11 z-50 w-52 surface py-1 shadow-lg">
              <div className="border-b px-3 py-2">
                <p className="truncate text-xs font-medium">{user.display_name}</p>
                <p className="truncate text-[11px] text-subtle capitalize">
                  {user.role.replace('_', ' ')}
                </p>
              </div>
              <button
                onClick={() => navigate('/profile')}
                className="flex w-full items-center gap-2 px-3 py-2 text-xs hover:bg-[var(--surface-sunken)]"
              >
                <UserIcon className="h-3.5 w-3.5" /> My profile
              </button>
              <button
                onClick={() => {
                  logout()
                  navigate('/login')
                }}
                className="flex w-full items-center gap-2 px-3 py-2 text-xs text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950/40"
              >
                <LogOut className="h-3.5 w-3.5" /> Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
