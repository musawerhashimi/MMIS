import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import type { MonographStage } from '@/types'

/** Merge Tailwind classes without conflicts. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * The colour a stage is shown in.
 *
 * One mapping used by charts, badges and the timeline, so a stage always
 * looks the same wherever it appears.
 */
/**
 * The colour a stage is drawn in.
 *
 * Literal values rather than CSS custom properties: SVG `fill` does not
 * reliably resolve `var(...)` across browsers, and charts are the main place
 * these are used. The palette matches the badge classes below.
 */
export const STAGE_COLOR: Record<MonographStage, string> = {
  draft: '#94a3b8',
  topic_submitted: '#f59e0b',
  topic_approved: '#10b981',
  proposal_submitted: '#f59e0b',
  under_review: '#3b82f6',
  revision_required: '#f97316',
  proposal_approved: '#10b981',
  research_in_progress: '#3b82f6',
  final_submission: '#f59e0b',
  final_review: '#6366f1',
  defense_scheduled: '#8b5cf6',
  defended: '#a855f7',
  completed: '#16a34a',
  rejected: '#ef4444',
  withdrawn: '#64748b',
}

/** Chart palette for anything not tied to a specific stage. */
export const CHART = {
  brand: '#2563eb',
  brandSoft: '#60a5fa',
  danger: '#ef4444',
  warn: '#f97316',
  grid: '#94a3b8',
} as const

/** Tailwind classes for a stage badge, light and dark. */
export const STAGE_BADGE: Record<MonographStage, string> = {
  draft: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
  topic_submitted: 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300',
  topic_approved: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300',
  proposal_submitted: 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300',
  under_review: 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300',
  revision_required: 'bg-orange-100 text-orange-800 dark:bg-orange-950 dark:text-orange-300',
  proposal_approved: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300',
  research_in_progress: 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300',
  final_submission: 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300',
  final_review: 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300',
  defense_scheduled: 'bg-violet-100 text-violet-800 dark:bg-violet-950 dark:text-violet-300',
  defended: 'bg-violet-100 text-violet-800 dark:bg-violet-950 dark:text-violet-300',
  completed: 'bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-300',
  rejected: 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300',
  withdrawn: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400',
}

/** Human wording for how long ago something happened. */
export function timeAgo(iso: string): string {
  const then = new Date(iso).getTime()
  const seconds = Math.floor((Date.now() - then) / 1000)

  if (seconds < 60) return 'just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? '' : 's'} ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} hour${hours === 1 ? '' : 's'} ago`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days} day${days === 1 ? '' : 's'} ago`
  const months = Math.floor(days / 30)
  if (months < 12) return `${months} month${months === 1 ? '' : 's'} ago`
  const years = Math.floor(months / 12)
  return `${years} year${years === 1 ? '' : 's'} ago`
}

export function formatDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export function formatDateTime(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function initials(name: string): string {
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')
}

/**
 * How urgent a wait is, for colouring "waiting 20 days" style figures.
 * Thresholds match the department's default response window.
 */
export function waitSeverity(days: number): 'ok' | 'warn' | 'late' {
  if (days >= 14) return 'late'
  if (days >= 7) return 'warn'
  return 'ok'
}
