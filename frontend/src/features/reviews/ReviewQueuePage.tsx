import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { CheckCircle2, Clock, Inbox } from 'lucide-react'
import { api } from '@/lib/api'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { StageBadge } from '@/components/ui/Badge'
import { EmptyState } from '@/components/ui/EmptyState'
import { TableSkeleton } from '@/components/ui/Skeleton'
import { StatTile } from '@/components/ui/StatTile'
import { cn, formatDateTime, waitSeverity } from '@/lib/utils'
import type { MonographListItem, Paginated, Review } from '@/types'

const WAIT_TONE = {
  ok: 'text-[var(--text-muted)]',
  warn: 'text-amber-600 dark:text-amber-400',
  late: 'text-red-600 dark:text-red-400 font-semibold',
}

/**
 * A supervisor's review queue.
 *
 * Two lists: what is waiting on them right now, and what they have already
 * decided. The waiting list is ordered by how long the student has been
 * waiting, because that is the fairest order to work through it.
 */
export function ReviewQueuePage() {
  const { data: waiting, isLoading } = useQuery({
    queryKey: ['monographs', 'awaiting-me'],
    queryFn: async () => {
      const { data } = await api.get<Paginated<MonographListItem>>('/monographs/awaiting_me/')
      return data
    },
  })

  const { data: given } = useQuery({
    queryKey: ['reviews', 'mine'],
    queryFn: async () => {
      const { data } = await api.get<Paginated<Review>>('/reviews/?ordering=-created_at')
      return data
    },
  })

  return (
    <>
      <PageHeader
        title="Reviews"
        description="Work waiting for your decision, and the feedback you have already given."
      />

      <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-3">
        <StatTile
          label="Waiting on you"
          value={waiting?.count ?? 0}
          icon={<Inbox className="h-4.5 w-4.5" />}
          tone={(waiting?.count ?? 0) > 0 ? 'warn' : 'good'}
        />
        <StatTile
          label="Reviews given"
          value={given?.count ?? 0}
          icon={<CheckCircle2 className="h-4.5 w-4.5" />}
        />
        <StatTile
          label="Longest wait"
          value={
            waiting?.results.length
              ? `${Math.max(...waiting.results.map((m) => m.days_in_current_stage))}d`
              : '—'
          }
          icon={<Clock className="h-4.5 w-4.5" />}
          tone={
            waiting?.results.length &&
            Math.max(...waiting.results.map((m) => m.days_in_current_stage)) >= 14
              ? 'danger'
              : 'default'
          }
        />
      </div>

      <Card className="mb-5">
        <CardHeader
          title="Waiting for your decision"
          description="Longest wait first — these students cannot move until you answer."
        />
        <CardBody className="p-0">
          {isLoading ? (
            <div className="p-5">
              <TableSkeleton rows={3} />
            </div>
          ) : !waiting?.results.length ? (
            <EmptyState
              icon={<CheckCircle2 className="h-5 w-5" />}
              title="Nothing waiting"
              description="You are up to date with every student."
            />
          ) : (
            <div className="divide-y">
              {waiting.results.map((m) => {
                const tone = waitSeverity(m.days_in_current_stage)
                return (
                  <Link
                    key={m.id}
                    to={`/monographs/${m.id}?tab=reviews`}
                    className="flex items-center gap-3 px-5 py-3.5 transition-colors hover:bg-[var(--surface-sunken)]"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">{m.title}</p>
                      <p className="mt-0.5 truncate text-[11px] text-muted">
                        {m.student_names.join(', ')}
                      </p>
                    </div>
                    <StageBadge stage={m.stage} label={m.stage_label} size="sm" />
                    <span className={cn('w-12 shrink-0 text-right text-xs tabular-nums', WAIT_TONE[tone])}>
                      {m.days_in_current_stage}d
                    </span>
                  </Link>
                )
              })}
            </div>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Feedback you have given" description="Most recent first" />
        <CardBody className="p-0">
          {!given?.results.length ? (
            <EmptyState title="No reviews yet" description="Your decisions will be listed here." />
          ) : (
            <div className="divide-y">
              {given.results.slice(0, 15).map((review) => (
                <Link
                  key={review.id}
                  to={`/monographs/${review.monograph}?tab=reviews`}
                  className="flex items-center gap-3 px-5 py-3 transition-colors hover:bg-[var(--surface-sunken)]"
                >
                  <span
                    className={cn(
                      'shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium',
                      review.decision === 'approved'
                        ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
                        : review.decision === 'rejected'
                          ? 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300'
                          : 'bg-orange-100 text-orange-800 dark:bg-orange-950 dark:text-orange-300',
                    )}
                  >
                    {review.decision_label}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-xs font-medium">
                      {review.summary || review.comments.slice(0, 60) || 'No summary'}
                    </p>
                    <p className="mt-0.5 text-[10px] text-subtle">
                      round {review.round_number}
                      {review.document_title && ` · ${review.document_title}`}
                    </p>
                  </div>
                  <span className="shrink-0 text-[10px] text-subtle">
                    {formatDateTime(review.created_at)}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </CardBody>
      </Card>
    </>
  )
}
