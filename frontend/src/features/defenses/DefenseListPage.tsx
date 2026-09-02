import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { CalendarClock, CalendarPlus, MapPin, Users } from 'lucide-react'
import { api } from '@/lib/api'
import { useAuth } from '@/stores/auth'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { EmptyState } from '@/components/ui/EmptyState'
import { TableSkeleton } from '@/components/ui/Skeleton'
import { cn, formatDateTime } from '@/lib/utils'
import { ScheduleDefenseDialog } from './ScheduleDefenseDialog'
import type { Defense, Paginated } from '@/types'

const RESULT_STYLE: Record<string, string> = {
  passed: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300',
  passed_with_revisions: 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300',
  failed: 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300',
}

export function DefenseListPage() {
  const user = useAuth((s) => s.user)
  const [scheduleOpen, setScheduleOpen] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['defenses'],
    queryFn: async () => {
      const { data } = await api.get<Paginated<Defense> | Defense[]>('/defenses/')
      return Array.isArray(data) ? data : data.results
    },
  })

  const upcoming = data?.filter((d) => d.is_upcoming) ?? []
  const past = data?.filter((d) => !d.is_upcoming) ?? []

  return (
    <>
      <PageHeader
        title="Defenses"
        description="Scheduled defenses, their committees, and the results."
        action={
          user?.permissions.is_head_of_department || user?.permissions.is_admin ? (
            <Button icon={<CalendarPlus className="h-4 w-4" />} onClick={() => setScheduleOpen(true)}>
              Schedule a defense
            </Button>
          ) : undefined
        }
      />

      {isLoading ? (
        <TableSkeleton rows={4} />
      ) : (
        <div className="space-y-5">
          <Card>
            <CardHeader
              title="Coming up"
              description={`${upcoming.length} defense${upcoming.length === 1 ? '' : 's'} scheduled`}
            />
            <CardBody className="p-0">
              {!upcoming.length ? (
                <EmptyState
                  icon={<CalendarClock className="h-5 w-5" />}
                  title="Nothing scheduled"
                  description="Defenses appear here once a date is set."
                />
              ) : (
                <div className="divide-y">
                  {upcoming.map((d) => (
                    <DefenseRow key={d.id} defense={d} />
                  ))}
                </div>
              )}
            </CardBody>
          </Card>

          {past.length > 0 && (
            <Card>
              <CardHeader title="Past defenses" description="With their recorded results" />
              <CardBody className="p-0">
                <div className="divide-y">
                  {past.map((d) => (
                    <DefenseRow key={d.id} defense={d} />
                  ))}
                </div>
              </CardBody>
            </Card>
          )}
        </div>
      )}

      <ScheduleDefenseDialog open={scheduleOpen} onClose={() => setScheduleOpen(false)} />
    </>
  )
}

function DefenseRow({ defense }: { defense: Defense }) {
  const read = defense.committee.filter((c) => c.has_read_monograph).length
  const scored = defense.committee.filter((c) => c.score != null).length

  return (
    <Link
      to={`/defenses/${defense.id}`}
      className="flex flex-wrap items-center gap-3 px-5 py-3.5 transition-colors hover:bg-[var(--surface-sunken)]"
    >
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{defense.monograph_title}</p>
        <p className="mt-0.5 truncate text-[11px] text-muted">
          {defense.student_names.join(', ')}
        </p>
        <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-subtle">
          <span className="inline-flex items-center gap-1">
            <CalendarClock className="h-3 w-3" />
            {formatDateTime(defense.scheduled_at)}
          </span>
          {defense.location && (
            <span className="inline-flex items-center gap-1">
              <MapPin className="h-3 w-3" />
              {defense.location}
            </span>
          )}
          <span className="inline-flex items-center gap-1">
            <Users className="h-3 w-3" />
            {defense.committee.length} member{defense.committee.length === 1 ? '' : 's'}
            {defense.is_upcoming
              ? ` · ${read} have read it`
              : ` · ${scored} scored`}
          </span>
        </div>
      </div>

      <div className="shrink-0 text-right">
        {defense.result ? (
          <>
            <Badge className={RESULT_STYLE[defense.result] ?? ''} size="sm">
              {defense.result_label}
            </Badge>
            {defense.final_grade && (
              <p className="mt-1 text-sm font-semibold tabular-nums">{defense.final_grade}</p>
            )}
          </>
        ) : (
          <Badge
            className={cn(
              'bg-violet-100 text-violet-800 dark:bg-violet-950 dark:text-violet-300',
            )}
            size="sm"
          >
            {defense.all_scores_in ? 'Awaiting result' : 'Scheduled'}
          </Badge>
        )}
      </div>
    </Link>
  )
}
