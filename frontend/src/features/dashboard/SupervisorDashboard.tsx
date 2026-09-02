import { Link } from 'react-router-dom'
import { BookOpen, CheckCircle2, Clock, Inbox, UserX } from 'lucide-react'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { StatTile } from '@/components/ui/StatTile'
import { EmptyState } from '@/components/ui/EmptyState'
import { StageBadge } from '@/components/ui/Badge'
import { StageDonut } from '@/components/charts/StageDonut'
import { cn, waitSeverity } from '@/lib/utils'
import type { SupervisorDashboard as Data } from '@/types'

const WAIT_TONE = {
  ok: 'text-[var(--text-muted)]',
  warn: 'text-amber-600 dark:text-amber-400',
  late: 'text-red-600 dark:text-red-400 font-semibold',
}

/**
 * A supervisor's working screen.
 *
 * "What needs answering today" comes first and everything else is secondary,
 * because that is the only question this person opens the system to ask.
 */
export function SupervisorDashboard({ data }: { data: Data }) {
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-3 gap-3">
        <StatTile
          label="Waiting on me"
          value={data.totals.awaiting_me}
          icon={<Inbox className="h-4.5 w-4.5" />}
          tone={data.totals.awaiting_me > 0 ? 'warn' : 'good'}
        />
        <StatTile
          label="Active students"
          value={data.totals.active}
          icon={<BookOpen className="h-4.5 w-4.5" />}
        />
        <StatTile
          label="Completed"
          value={data.totals.completed}
          icon={<CheckCircle2 className="h-4.5 w-4.5" />}
          tone="good"
        />
      </div>

      <Card>
        <CardHeader
          title="Waiting for your response"
          description="Longest wait first"
          action={<Clock className="h-4 w-4 text-subtle" />}
        />
        <CardBody className="p-0">
          {!data.awaiting_me.length ? (
            <EmptyState
              icon={<CheckCircle2 className="h-5 w-5" />}
              title="Nothing waiting"
              description="You are up to date with every student."
            />
          ) : (
            <div className="divide-y">
              {data.awaiting_me.map((row) => {
                const tone = waitSeverity(row.waiting_days)
                return (
                  <Link
                    key={row.id}
                    to={`/monographs/${row.id}`}
                    className="flex items-center gap-3 px-5 py-3 transition-colors hover:bg-[var(--surface-sunken)]"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">{row.title}</p>
                      <p className="mt-0.5 truncate text-[11px] text-muted">
                        {row.students.join(', ')}
                      </p>
                    </div>
                    <StageBadge stage={row.stage} label={row.stage_label} size="sm" />
                    <span className={cn('shrink-0 text-xs tabular-nums', WAIT_TONE[tone])}>
                      {row.waiting_days}d
                    </span>
                  </Link>
                )
              })}
            </div>
          )}
        </CardBody>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader
            title="Students who have gone quiet"
            description="No progress for a month or more"
            action={<UserX className="h-4 w-4 text-subtle" />}
          />
          <CardBody className="p-0">
            {!data.gone_quiet.length ? (
              <EmptyState title="Everyone is moving" description="No student has stalled." />
            ) : (
              <div className="divide-y">
                {data.gone_quiet.map((row) => (
                  <Link
                    key={row.id}
                    to={`/monographs/${row.id}`}
                    className="flex items-center gap-3 px-5 py-3 transition-colors hover:bg-[var(--surface-sunken)]"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-xs font-medium">{row.title}</p>
                      <p className="mt-0.5 truncate text-[11px] text-muted">
                        {row.students.join(', ')} · {row.stage_label}
                      </p>
                    </div>
                    <span className="shrink-0 text-xs font-semibold tabular-nums text-red-600 dark:text-red-400">
                      {row.silent_days}d
                    </span>
                  </Link>
                ))}
              </div>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Your students by stage" />
          <CardBody className="pt-2">
            <StageDonut data={data.by_stage} height={230} />
          </CardBody>
        </Card>
      </div>
    </div>
  )
}
