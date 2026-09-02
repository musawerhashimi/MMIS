import { Link } from 'react-router-dom'
import {
  CalendarClock, FileText, MessageSquare, PlusCircle, Sparkles,
} from 'lucide-react'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { EmptyState } from '@/components/ui/EmptyState'
import { StageBadge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { ProgressRing } from '@/components/charts/ProgressRing'
import { StageTrack } from '@/components/charts/StageTrack'
import { cn, formatDate, formatDateTime, STAGE_COLOR, timeAgo } from '@/lib/utils'
import type { StudentDashboard as Data } from '@/types'

const DECISION_STYLE = {
  approved: 'border-emerald-200 bg-emerald-50 dark:border-emerald-900 dark:bg-emerald-950/40',
  revision_requested: 'border-orange-200 bg-orange-50 dark:border-orange-900 dark:bg-orange-950/40',
  rejected: 'border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950/40',
}

/**
 * The student's screen.
 *
 * Answers the three things they open the system to find out: where am I, what
 * did my supervisor say, and when is my next deadline.
 */
export function StudentDashboard({ data }: { data: Data }) {
  if (!data.monograph) {
    return (
      <Card>
        <CardBody>
          <EmptyState
            icon={<Sparkles className="h-5 w-5" />}
            title="You have not started a monograph yet"
            description="Propose your topic to begin. You can change it freely until you submit it."
            action={
              <Link to="/monographs/new">
                <Button icon={<PlusCircle className="h-4 w-4" />}>Propose a topic</Button>
              </Link>
            }
          />
        </CardBody>
      </Card>
    )
  }

  const m = data.monograph
  const deadline = data.next_deadline

  return (
    <div className="space-y-5">
      <Card>
        <CardBody>
          <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
            <ProgressRing
              value={m.progress_percent}
              color={STAGE_COLOR[m.stage]}
              sublabel="complete"
            />
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <StageBadge stage={m.stage} label={m.stage_label} />
                <span className="text-[11px] text-subtle">
                  {m.days_in_current_stage} day{m.days_in_current_stage === 1 ? '' : 's'} at this stage
                </span>
              </div>
              <h2 className="mt-2 text-base font-semibold leading-snug">{m.title}</h2>
              <p className="mt-1 text-xs text-muted">
                {m.supervisor ? `Supervised by ${m.supervisor}` : 'No supervisor assigned yet'}
              </p>
              <Link
                to={`/monographs/${m.id}`}
                className="mt-3 inline-block text-xs font-medium text-brand-600 hover:underline dark:text-brand-400"
              >
                Open my monograph →
              </Link>
            </div>
          </div>

          <div className="mt-6 border-t pt-5">
            <StageTrack current={m.stage} />
          </div>
        </CardBody>
      </Card>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader
            title="Latest feedback"
            description="What your supervisor said most recently"
            action={<MessageSquare className="h-4 w-4 text-subtle" />}
          />
          <CardBody>
            {!data.latest_feedback ? (
              <EmptyState
                title="No feedback yet"
                description="Your supervisor's comments will appear here once they review your work."
              />
            ) : (
              <div
                className={cn(
                  'rounded-lg border p-4',
                  DECISION_STYLE[data.latest_feedback.decision],
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <p className="text-xs font-semibold">
                    {data.latest_feedback.summary || 'Feedback received'}
                  </p>
                  <span className="shrink-0 text-[10px] text-muted">
                    {timeAgo(data.latest_feedback.at)}
                  </span>
                </div>
                {data.latest_feedback.comments && (
                  <p className="mt-2 whitespace-pre-line text-xs leading-relaxed">
                    {data.latest_feedback.comments}
                  </p>
                )}
                <p className="mt-3 text-[11px] text-muted">
                  — {data.latest_feedback.reviewer}
                </p>
              </div>
            )}
          </CardBody>
        </Card>

        <div className="space-y-4">
          {deadline && (
            <Card>
              <CardHeader title="Next deadline" action={<CalendarClock className="h-4 w-4 text-subtle" />} />
              <CardBody>
                <p className="text-2xl font-semibold tabular-nums">
                  {deadline.days_remaining}
                  <span className="ml-1 text-xs font-normal text-muted">
                    day{deadline.days_remaining === 1 ? '' : 's'} left
                  </span>
                </p>
                <p className="mt-1 text-xs text-muted">
                  {deadline.description || deadline.stage.replace(/_/g, ' ')}
                </p>
                <p className="mt-0.5 text-[11px] text-subtle">{formatDate(deadline.due_date)}</p>
              </CardBody>
            </Card>
          )}

          {data.defense?.scheduled_at && (
            <Card>
              <CardHeader title="Your defense" />
              <CardBody>
                <p className="text-sm font-semibold">{formatDateTime(data.defense.scheduled_at)}</p>
                <p className="mt-1 text-xs text-muted">{data.defense.location || 'Location to be confirmed'}</p>
                {data.defense.final_grade && (
                  <p className="mt-3 text-xs">
                    Final grade:{' '}
                    <span className="text-base font-semibold tabular-nums">
                      {data.defense.final_grade}
                    </span>
                  </p>
                )}
              </CardBody>
            </Card>
          )}

          <Card>
            <CardHeader title="Your documents" action={<FileText className="h-4 w-4 text-subtle" />} />
            <CardBody>
              <p className="text-2xl font-semibold tabular-nums">{data.documents}</p>
              <p className="mt-1 text-xs text-muted">
                file{data.documents === 1 ? '' : 's'} submitted
              </p>
              <Link
                to={`/monographs/${m.id}?tab=documents`}
                className="mt-3 inline-block text-xs font-medium text-brand-600 hover:underline dark:text-brand-400"
              >
                Manage documents →
              </Link>
            </CardBody>
          </Card>
        </div>
      </div>
    </div>
  )
}
