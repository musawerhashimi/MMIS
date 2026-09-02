import { Link } from 'react-router-dom'
import {
  AlertTriangle, BookOpen, CheckCircle2, Clock, TrendingUp, UserX, Users,
} from 'lucide-react'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { StatTile } from '@/components/ui/StatTile'
import { EmptyState } from '@/components/ui/EmptyState'
import { StageDonut } from '@/components/charts/StageDonut'
import { WorkloadChart } from '@/components/charts/WorkloadChart'
import { BottleneckChart } from '@/components/charts/BottleneckChart'
import { cn, timeAgo } from '@/lib/utils'
import type { HodDashboard as Data } from '@/types'

/**
 * The department's whole picture on one screen.
 *
 * The top row is deliberately the four questions a head of department used to
 * have to ring round every supervisor to answer.
 */
export function HodDashboard({ data }: { data: Data }) {
  const { totals, attention } = data

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile
          label="Active"
          value={totals.active}
          icon={<BookOpen className="h-4.5 w-4.5" />}
          hint={`${totals.total} in total`}
          to="/monographs?active=true"
        />
        <StatTile
          label="Awaiting review"
          value={attention.awaiting_supervisor}
          icon={<Clock className="h-4.5 w-4.5" />}
          tone={attention.awaiting_supervisor > 0 ? 'warn' : 'default'}
          hint="past the agreed response time"
          to="/monographs?awaiting=true"
        />
        <StatTile
          label="Gone quiet"
          value={attention.gone_quiet}
          icon={<UserX className="h-4.5 w-4.5" />}
          tone={attention.gone_quiet > 0 ? 'danger' : 'default'}
          hint="no movement for weeks"
          to="/reports/behind-schedule"
        />
        <StatTile
          label="Completed"
          value={totals.completed}
          icon={<CheckCircle2 className="h-4.5 w-4.5" />}
          tone="good"
          hint="defended and archived"
          to="/monographs?active=false"
        />
      </div>

      {totals.unassigned > 0 && (
        <Link
          to="/monographs?unassigned=true"
          className="flex items-center gap-3 rounded-lg border-[1.5px] border-amber-300 bg-amber-50 px-4 py-3 transition-colors hover:bg-amber-100 dark:border-amber-800 dark:bg-amber-950/50 dark:hover:bg-amber-950/70"
        >
          <AlertTriangle className="h-4.5 w-4.5 shrink-0 text-amber-600 dark:text-amber-400" />
          <p className="text-xs text-amber-800 dark:text-amber-200">
            <strong>{totals.unassigned}</strong>{' '}
            {totals.unassigned === 1 ? 'monograph has' : 'monographs have'} no supervisor yet.
          </p>
        </Link>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardHeader title="Where everyone is" description="Monographs by stage" />
          <CardBody className="pt-2">
            <StageDonut data={data.by_stage} />
          </CardBody>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader
            title="Supervisor workload"
            description="Red means over the agreed limit"
            action={
              <Link to="/reports" className="text-xs text-brand-600 hover:underline dark:text-brand-400">
                Full report
              </Link>
            }
          />
          <CardBody className="pt-2">
            <WorkloadChart data={data.supervisor_load} />
          </CardBody>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader
            title="Where the time goes"
            description="Average days spent at each stage"
            action={<TrendingUp className="h-4 w-4 text-subtle" />}
          />
          <CardBody className="pt-2">
            <BottleneckChart data={data.bottlenecks} />
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Recent activity" description="The last things that happened" />
          <CardBody className="p-0">
            {!data.recent_activity.length ? (
              <EmptyState
                icon={<Users className="h-5 w-5" />}
                title="Nothing has happened yet"
                description="Activity will appear here as students and supervisors work."
              />
            ) : (
              <div className="max-h-[280px] divide-y overflow-y-auto">
                {data.recent_activity.map((entry, index) => (
                  <Link
                    key={`${entry.monograph_id}-${index}`}
                    to={`/monographs/${entry.monograph_id}`}
                    className="flex items-start gap-3 px-5 py-3 transition-colors hover:bg-[var(--surface-sunken)]"
                  >
                    <span
                      className={cn(
                        'mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full',
                        index === 0 ? 'bg-brand-500' : 'bg-[var(--border-strong)]',
                      )}
                    />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-xs font-medium">{entry.title}</p>
                      <p className="mt-0.5 text-[11px] text-muted">
                        {entry.to_stage_label}
                        {entry.actor && ` · ${entry.actor}`}
                      </p>
                    </div>
                    <span className="shrink-0 text-[10px] text-subtle">{timeAgo(entry.at)}</span>
                  </Link>
                ))}
              </div>
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  )
}
