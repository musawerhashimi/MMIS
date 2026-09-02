import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { CalendarCheck } from 'lucide-react'
import { api } from '@/lib/api'
import { useAuth } from '@/stores/auth'
import { useWebSocket } from '@/hooks/useWebSocket'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { CardSkeleton } from '@/components/ui/Skeleton'
import { EmptyState } from '@/components/ui/EmptyState'
import { formatDateTime } from '@/lib/utils'
import { HodDashboard } from './HodDashboard'
import { SupervisorDashboard } from './SupervisorDashboard'
import { StudentDashboard } from './StudentDashboard'
import type { CommitteeDashboard, Dashboard } from '@/types'

/**
 * The first screen after signing in.
 *
 * The server decides which dashboard this person needs, so the client asks
 * once and renders whichever shape comes back.
 */
export function DashboardPage() {
  const user = useAuth((s) => s.user)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: async () => {
      const { data } = await api.get<Dashboard>('/reports/dashboard/')
      return data
    },
  })

  // Staff watch department-wide figures, which change as other people work.
  useWebSocket({
    path: user?.permissions.can_supervise || user?.permissions.is_admin ? '/ws/dashboard/' : null,
    onMessage: (raw) => {
      const message = raw as { event?: string }
      if (message.event === 'dashboard_changed') {
        queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      }
    },
  })

  const greeting = user ? `Welcome back, ${user.full_name.split(' ')[0]}` : 'Dashboard'

  if (isLoading || !data) {
    return (
      <>
        <PageHeader title={greeting} />
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <CardSkeleton key={i} rows={1} />
          ))}
        </div>
        <div className="mt-4 grid gap-4 lg:grid-cols-3">
          <CardSkeleton rows={6} />
          <div className="lg:col-span-2">
            <CardSkeleton rows={6} />
          </div>
        </div>
      </>
    )
  }

  return (
    <>
      <PageHeader
        title={greeting}
        description={
          data.role === 'head_of_department'
            ? 'How your department is doing right now.'
            : data.role === 'supervisor'
              ? 'What is waiting for your attention.'
              : data.role === 'student'
                ? 'Where your monograph stands.'
                : 'The monographs you are examining.'
        }
      />
      {data.role === 'head_of_department' && <HodDashboard data={data} />}
      {data.role === 'supervisor' && <SupervisorDashboard data={data} />}
      {data.role === 'student' && <StudentDashboard data={data} />}
      {data.role === 'committee' && <CommitteeView data={data} />}
    </>
  )
}

function CommitteeView({ data }: { data: CommitteeDashboard }) {
  return (
    <Card>
      <CardHeader
        title="Monographs you are examining"
        description="Read each one before its defense date"
        action={<CalendarCheck className="h-4 w-4 text-subtle" />}
      />
      <CardBody className="p-0">
        {!data.assigned_defenses.length ? (
          <EmptyState
            title="Nothing assigned"
            description="You are not on any defense committee at the moment."
          />
        ) : (
          <div className="divide-y">
            {data.assigned_defenses.map((defense) => (
              <Link
                key={defense.id}
                to={`/defenses/${defense.id}`}
                className="flex items-center gap-3 px-5 py-3.5 transition-colors hover:bg-[var(--surface-sunken)]"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{defense.monograph_title}</p>
                  <p className="mt-0.5 truncate text-[11px] text-muted">
                    {defense.student_names.join(', ')} · {defense.location || 'Location to be confirmed'}
                  </p>
                </div>
                <span className="shrink-0 text-xs text-muted">
                  {formatDateTime(defense.scheduled_at)}
                </span>
              </Link>
            ))}
          </div>
        )}
      </CardBody>
    </Card>
  )
}
