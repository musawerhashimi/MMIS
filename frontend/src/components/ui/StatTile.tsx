import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { cn } from '@/lib/utils'

interface Props {
  label: string
  value: ReactNode
  icon?: ReactNode
  hint?: string
  tone?: 'default' | 'warn' | 'danger' | 'good'
  to?: string
  className?: string
}

const TONES = {
  default: 'text-[var(--text)]',
  good: 'text-emerald-600 dark:text-emerald-400',
  warn: 'text-amber-600 dark:text-amber-400',
  danger: 'text-red-600 dark:text-red-400',
}

const ICON_TONES = {
  default: 'bg-[var(--surface-sunken)] text-[var(--text-muted)]',
  good: 'bg-emerald-50 text-emerald-600 dark:bg-emerald-950/60 dark:text-emerald-400',
  warn: 'bg-amber-50 text-amber-600 dark:bg-amber-950/60 dark:text-amber-400',
  danger: 'bg-red-50 text-red-600 dark:bg-red-950/60 dark:text-red-400',
}

/**
 * One headline number.
 *
 * Made clickable wherever the number leads somewhere: a count of students
 * behind schedule is only useful if you can get to the list of them.
 */
export function StatTile({ label, value, icon, hint, tone = 'default', to, className }: Props) {
  const body = (
    <div
      className={cn(
        'surface flex items-start gap-3 p-4 transition-shadow',
        to && 'hover:shadow-md cursor-pointer',
        className,
      )}
    >
      {icon && (
        <div className={cn('flex h-9 w-9 shrink-0 items-center justify-center rounded-lg', ICON_TONES[tone])}>
          {icon}
        </div>
      )}
      <div className="min-w-0">
        <p className="text-[11px] font-medium uppercase tracking-wide text-subtle">{label}</p>
        <p className={cn('mt-0.5 text-2xl font-semibold tabular-nums leading-none', TONES[tone])}>
          {value}
        </p>
        {hint && <p className="mt-1 text-[11px] text-muted">{hint}</p>}
      </div>
    </div>
  )

  return to ? <Link to={to}>{body}</Link> : body
}
