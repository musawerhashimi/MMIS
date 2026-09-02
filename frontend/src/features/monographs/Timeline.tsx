import { useQuery } from '@tanstack/react-query'
import { FileText, GitCommitHorizontal, MessageSquare, UserCheck } from 'lucide-react'
import { api } from '@/lib/api'
import { EmptyState } from '@/components/ui/EmptyState'
import { Skeleton } from '@/components/ui/Skeleton'
import { formatDateTime, STAGE_COLOR, timeAgo } from '@/lib/utils'
import type { MonographStage, TimelineEntry } from '@/types'

const ACTIVITY_ICON: Record<string, typeof FileText> = {
  document_uploaded: FileText,
  document_approved: FileText,
  supervisor_assigned: UserCheck,
  review_submitted: MessageSquare,
  message_posted: MessageSquare,
}

/**
 * Everything that has happened to this monograph, newest first.
 *
 * This is the record that settles disagreements: who did what, and when. It
 * cannot be edited from anywhere in the application.
 */
export function Timeline({ monographId }: { monographId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ['monograph', monographId, 'timeline'],
    queryFn: async () => {
      const { data } = await api.get<TimelineEntry[]>(`/monographs/${monographId}/timeline/`)
      return data
    },
  })

  if (isLoading) {
    return (
      <div className="space-y-3 p-5">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-14 w-full" />
        ))}
      </div>
    )
  }

  if (!data?.length) {
    return <EmptyState title="Nothing recorded yet" description="Actions will appear here as they happen." />
  }

  return (
    <div className="relative px-5 py-4">
      {/* The spine the entries hang off. */}
      <div className="absolute bottom-4 left-[34px] top-4 w-px bg-[var(--border)]" />

      <div className="space-y-4">
        {data.map((entry) => {
          const isTransition = entry.type === 'transition'
          const color = isTransition
            ? STAGE_COLOR[entry.to_stage as MonographStage] ?? 'var(--border-strong)'
            : 'var(--border-strong)'
          const Icon = isTransition
            ? GitCommitHorizontal
            : ACTIVITY_ICON[entry.action] ?? GitCommitHorizontal

          return (
            <div key={entry.id} className="relative flex gap-3">
              <div
                className="relative z-10 flex h-[26px] w-[26px] shrink-0 items-center justify-center rounded-full border-2 bg-[var(--surface-raised)]"
                style={{ borderColor: color }}
              >
                <Icon className="h-3 w-3" style={{ color }} />
              </div>

              <div className="min-w-0 flex-1 pb-1">
                <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                  <p className="text-xs font-medium">
                    {isTransition ? entry.to_stage_label : entry.description}
                  </p>
                  <span className="shrink-0 text-[10px] text-subtle" title={formatDateTime(entry.created_at)}>
                    {timeAgo(entry.created_at)}
                  </span>
                </div>

                <p className="mt-0.5 text-[11px] text-muted">
                  {entry.actor?.full_name ?? 'System'}
                  {isTransition && entry.days_in_previous_stage != null && entry.from_stage && (
                    <> · after {entry.days_in_previous_stage} day{entry.days_in_previous_stage === 1 ? '' : 's'}</>
                  )}
                </p>

                {isTransition && entry.note && (
                  <p className="mt-1.5 whitespace-pre-line rounded-lg surface-sunken px-3 py-2 text-[11px] leading-relaxed">
                    {entry.note}
                  </p>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
