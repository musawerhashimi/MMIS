import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, Download, TrendingUp, Users } from 'lucide-react'
import { toast } from 'sonner'
import { api, errorMessage, tokens } from '@/lib/api'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { StatTile } from '@/components/ui/StatTile'
import { EmptyState } from '@/components/ui/EmptyState'
import { CardSkeleton } from '@/components/ui/Skeleton'
import { StageBars } from '@/components/charts/StageBars'
import { WorkloadChart } from '@/components/charts/WorkloadChart'
import { BottleneckChart } from '@/components/charts/BottleneckChart'
import { cn } from '@/lib/utils'
import type { Bottleneck, StageCount, SupervisorLoad } from '@/types'

interface Progress {
  totals: { total: number; active: number; completed: number }
  completion_rate: number
  average_grade: number | null
  by_stage: StageCount[]
}

interface BehindRow {
  id: string
  title: string
  students: string[]
  supervisor: string | null
  stage_label: string
  stuck_days: number
  progress_percent: number
}

/**
 * The reports a department sends to the faculty.
 *
 * Everything here is derived at read time from the monograph tables, so the
 * numbers can never drift from what the system actually holds.
 */
export function ReportsPage() {
  const { data: progress, isLoading } = useQuery({
    queryKey: ['reports', 'progress'],
    queryFn: async () => {
      const { data } = await api.get<Progress>('/reports/progress/')
      return data
    },
  })

  const { data: workload } = useQuery({
    queryKey: ['reports', 'workload'],
    queryFn: async () => {
      const { data } = await api.get<SupervisorLoad[]>('/reports/workload/')
      return data
    },
  })

  const { data: bottlenecks } = useQuery({
    queryKey: ['reports', 'bottlenecks'],
    queryFn: async () => {
      const { data } = await api.get<Bottleneck[]>('/reports/bottlenecks/')
      return data
    },
  })

  const { data: behind } = useQuery({
    queryKey: ['reports', 'behind'],
    queryFn: async () => {
      const { data } = await api.get<BehindRow[]>('/reports/behind-schedule/?days=30')
      return data
    },
  })

  async function exportCsv() {
    try {
      const response = await fetch('/api/v1/reports/export/monographs/', {
        headers: { Authorization: `Bearer ${tokens.access}` },
      })
      if (!response.ok) throw new Error('The export could not be produced.')
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'monographs.csv'
      link.click()
      URL.revokeObjectURL(url)
      toast.success('Export downloaded')
    } catch (error) {
      toast.error(errorMessage(error))
    }
  }

  if (isLoading) {
    return (
      <>
        <PageHeader title="Reports" />
        <CardSkeleton rows={6} />
      </>
    )
  }

  return (
    <>
      <PageHeader
        title="Reports"
        description="How the department is doing, and where the time goes."
        action={
          <Button variant="secondary" icon={<Download className="h-4 w-4" />} onClick={exportCsv}>
            Export as CSV
          </Button>
        }
      />

      <div className="mb-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile label="Total" value={progress?.totals.total ?? 0} />
        <StatTile label="Active" value={progress?.totals.active ?? 0} />
        <StatTile
          label="Completed"
          value={progress?.totals.completed ?? 0}
          tone="good"
          hint={`${progress?.completion_rate ?? 0}% completion rate`}
        />
        <StatTile
          label="Average grade"
          value={progress?.average_grade ?? '—'}
          hint="across completed monographs"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Progress by stage" description="Where every monograph stands" />
          <CardBody className="pt-2">
            <StageBars data={progress?.by_stage ?? []} />
          </CardBody>
        </Card>

        <Card>
          <CardHeader
            title="Supervisor workload"
            description="Red means over the agreed limit"
            action={<Users className="h-4 w-4 text-subtle" />}
          />
          <CardBody className="pt-2">
            <WorkloadChart data={workload ?? []} />
          </CardBody>
        </Card>

        <Card>
          <CardHeader
            title="Where the time goes"
            description="Average days spent at each stage"
            action={<TrendingUp className="h-4 w-4 text-subtle" />}
          />
          <CardBody className="pt-2">
            <BottleneckChart data={bottlenecks ?? []} />
          </CardBody>
        </Card>

        <Card>
          <CardHeader
            title="Behind schedule"
            description="No movement for 30 days or more"
            action={<AlertTriangle className="h-4 w-4 text-subtle" />}
          />
          <CardBody className="p-0">
            {!behind?.length ? (
              <EmptyState title="Everyone is moving" description="No student has stalled." />
            ) : (
              <div className="max-h-[280px] divide-y overflow-y-auto">
                {behind.map((row) => (
                  <Link
                    key={row.id}
                    to={`/monographs/${row.id}`}
                    className="flex items-center gap-3 px-5 py-3 transition-colors hover:bg-[var(--surface-sunken)]"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-xs font-medium">{row.title}</p>
                      <p className="mt-0.5 truncate text-[11px] text-muted">
                        {row.students.join(', ')} · {row.stage_label}
                        {row.supervisor && ` · ${row.supervisor}`}
                      </p>
                    </div>
                    <span
                      className={cn(
                        'shrink-0 text-xs font-semibold tabular-nums',
                        row.stuck_days >= 60
                          ? 'text-red-600 dark:text-red-400'
                          : 'text-amber-600 dark:text-amber-400',
                      )}
                    >
                      {row.stuck_days}d
                    </span>
                  </Link>
                ))}
              </div>
            )}
          </CardBody>
        </Card>
      </div>
    </>
  )
}
