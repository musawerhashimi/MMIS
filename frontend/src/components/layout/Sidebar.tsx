import { NavLink } from 'react-router-dom'
import {
  Archive, BarChart3, BookOpen, Building2, Calendar, FileText,
  GraduationCap, LayoutDashboard, Settings, Users,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuth } from '@/stores/auth'
import type { Permissions } from '@/types'

interface Item {
  to: string
  label: string
  icon: typeof LayoutDashboard
  /** Who may see this entry. Everyone, when omitted. */
  visible?: (p: Permissions) => boolean
}

const ITEMS: Item[] = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/monographs', label: 'Monographs', icon: BookOpen },
  {
    to: '/reviews',
    label: 'Reviews',
    icon: FileText,
    visible: (p) => p.can_supervise || p.is_admin,
  },
  { to: '/defenses', label: 'Defenses', icon: Calendar },
  { to: '/archive', label: 'Archive', icon: Archive },
  {
    to: '/reports',
    label: 'Reports',
    icon: BarChart3,
    visible: (p) => p.is_head_of_department || p.is_admin,
  },
  {
    to: '/people',
    label: 'People',
    icon: Users,
    visible: (p) => p.is_head_of_department || p.is_admin,
  },
  {
    to: '/departments',
    label: 'Departments',
    icon: Building2,
    visible: (p) => p.is_admin,
  },
  {
    to: '/settings',
    label: 'Settings',
    icon: Settings,
    visible: (p) => p.is_head_of_department || p.is_admin,
  },
]

export function Sidebar({ collapsed, onNavigate }: { collapsed: boolean; onNavigate?: () => void }) {
  const user = useAuth((s) => s.user)
  if (!user) return null

  const items = ITEMS.filter((item) => !item.visible || item.visible(user.permissions))

  return (
    <aside
      className={cn(
        'flex h-full flex-col border-r bg-[var(--surface-raised)] transition-[width] duration-200',
        collapsed ? 'w-16' : 'w-60',
      )}
    >
      <div className={cn('flex h-14 items-center gap-2.5 border-b px-4', collapsed && 'justify-center px-0')}>
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-600 text-white">
          <GraduationCap className="h-4.5 w-4.5" />
        </div>
        {!collapsed && (
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold leading-tight">Monograph</p>
            <p className="truncate text-[10px] text-subtle leading-tight">Management System</p>
          </div>
        )}
      </div>

      <nav className="flex-1 space-y-0.5 overflow-y-auto p-2">
        {items.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            onClick={onNavigate}
            title={collapsed ? label : undefined}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                collapsed && 'justify-center px-0',
                isActive
                  ? 'bg-brand-50 text-brand-700 dark:bg-brand-950/60 dark:text-brand-300'
                  : 'text-[var(--text-muted)] hover:bg-[var(--surface-sunken)] hover:text-[var(--text)]',
              )
            }
          >
            <Icon className="h-4.5 w-4.5 shrink-0" />
            {!collapsed && <span className="truncate">{label}</span>}
          </NavLink>
        ))}
      </nav>

      {!collapsed && (
        <div className="border-t p-3">
          <p className="truncate text-xs font-medium">{user.display_name}</p>
          <p className="truncate text-[11px] text-subtle">
            {user.department_name ?? 'No department'}
          </p>
        </div>
      )}
    </aside>
  )
}
