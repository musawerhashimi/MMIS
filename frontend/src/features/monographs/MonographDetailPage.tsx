import { useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft, Clock, FileText, History, MessageSquare, Printer, UserPlus, Wifi, WifiOff,
} from 'lucide-react'
import { toast } from 'sonner'
import { api, errorMessage } from '@/lib/api'
import { useAuth } from '@/stores/auth'
import { useWebSocket } from '@/hooks/useWebSocket'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card, CardBody } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { Select } from '@/components/ui/Input'
import { StageBadge } from '@/components/ui/Badge'
import { CardSkeleton } from '@/components/ui/Skeleton'
import { ProgressRing } from '@/components/charts/ProgressRing'
import { StageTrack } from '@/components/charts/StageTrack'
import { cn, formatDate, STAGE_COLOR } from '@/lib/utils'
import { Timeline } from './Timeline'
import { DocumentsPanel } from './DocumentsPanel'
import { ReviewsPanel } from './ReviewsPanel'
import { TransitionDialog } from './TransitionDialog'
import type { AvailableAction, Monograph, SupervisorOption } from '@/types'

type Tab = 'overview' | 'documents' | 'reviews' | 'history'

const TABS: { id: Tab; label: string; icon: typeof FileText }[] = [
  { id: 'overview', label: 'Overview', icon: FileText },
  { id: 'documents', label: 'Documents', icon: FileText },
  { id: 'reviews', label: 'Feedback', icon: MessageSquare },
  { id: 'history', label: 'History', icon: History },
]

/**
 * One monograph, in full.
 *
 * Open on a supervisor's and a student's screen at the same time, this stays
 * in step: a decision written on one appears on the other without a reload.
 */
export function MonographDetailPage() {
  const { id = '' } = useParams()
  const [params, setParams] = useSearchParams()
  const user = useAuth((s) => s.user)
  const queryClient = useQueryClient()

  const tab = (params.get('tab') as Tab) ?? 'overview'
  const [pendingAction, setPendingAction] = useState<AvailableAction | null>(null)
  const [assignOpen, setAssignOpen] = useState(false)

  const { data: m, isLoading } = useQuery({
    queryKey: ['monograph', id],
    queryFn: async () => {
      const { data } = await api.get<Monograph>(`/monographs/${id}/`)
      return data
    },
  })

  const { status } = useWebSocket({
    path: id ? `/ws/monographs/${id}/` : null,
    onMessage: (raw) => {
      const message = raw as { event?: string; data?: Record<string, unknown> }
      if (!message.event || message.event === 'connected') return

      // Someone else changed something. Refetch rather than patching state by
      // hand, so the screen can never drift from what the server holds.
      queryClient.invalidateQueries({ queryKey: ['monograph', id] })
      queryClient.invalidateQueries({ queryKey: ['documents', id] })
      queryClient.invalidateQueries({ queryKey: ['reviews', id] })

      if (message.event === 'stage_changed') {
        toast.info('This monograph moved', {
          description: String(message.data?.to_stage ?? '').replace(/_/g, ' '),
        })
      }
    },
  })

  if (isLoading || !m) {
    return (
      <>
        <PageHeader title="Loading" />
        <CardSkeleton rows={6} />
      </>
    )
  }

  const canApprove = Boolean(
    user?.permissions.is_admin ||
      user?.permissions.is_head_of_department ||
      m.supervisor?.id === user?.id,
  )
  const isStudent = Boolean(user?.permissions.is_student)
  const canReview = canApprove && !isStudent

  return (
    <>
      <PageHeader
        breadcrumb={
          <Link to="/monographs" className="inline-flex items-center gap-1 hover:underline">
            <ArrowLeft className="h-3 w-3" /> All monographs
          </Link>
        }
        title={m.title}
        description={`${m.student_names.join(', ')} · ${m.department_name} · ${m.academic_year_name}`}
        action={
          <div className="flex items-center gap-2">
            <span
              className="flex items-center gap-1 text-[10px] text-subtle"
              title={status === 'open' ? 'Live updates are on' : 'Reconnecting'}
            >
              {status === 'open' ? (
                <Wifi className="h-3 w-3 text-emerald-500" />
              ) : (
                <WifiOff className="h-3 w-3" />
              )}
              {status === 'open' ? 'Live' : 'Offline'}
            </span>

            {user?.permissions.is_head_of_department && !m.is_finished && (
              <Button
                variant="secondary"
                size="sm"
                icon={<UserPlus className="h-3.5 w-3.5" />}
                onClick={() => setAssignOpen(true)}
              >
                {m.supervisor ? 'Change supervisor' : 'Assign supervisor'}
              </Button>
            )}

            {!isStudent && (
              <Link to={`/monographs/${id}/forms`}>
                <Button variant="secondary" size="sm" icon={<Printer className="h-3.5 w-3.5" />}>
                  Forms
                </Button>
              </Link>
            )}
          </div>
        }
      />

      <Card className="mb-4">
        <CardBody>
          <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
            <ProgressRing value={m.progress_percent} color={STAGE_COLOR[m.stage]} sublabel="complete" />

            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <StageBadge stage={m.stage} label={m.stage_label} />
                <span className="inline-flex items-center gap-1 text-[11px] text-subtle">
                  <Clock className="h-3 w-3" />
                  {m.days_in_current_stage} day{m.days_in_current_stage === 1 ? '' : 's'} here
                </span>
              </div>

              <dl className="mt-3 grid grid-cols-2 gap-x-6 gap-y-1.5 text-xs sm:grid-cols-3">
                <div>
                  <dt className="text-subtle">Supervisor</dt>
                  <dd className="font-medium">{m.supervisor?.display_name ?? 'Not assigned'}</dd>
                </div>
                <div>
                  <dt className="text-subtle">Research area</dt>
                  <dd className="font-medium">{m.research_area_name ?? '—'}</dd>
                </div>
                <div>
                  <dt className="text-subtle">Started</dt>
                  <dd className="font-medium">{formatDate(m.created_at)}</dd>
                </div>
                {m.final_grade && (
                  <div>
                    <dt className="text-subtle">Final grade</dt>
                    <dd className="text-sm font-semibold tabular-nums">{m.final_grade}</dd>
                  </div>
                )}
              </dl>
            </div>
          </div>

          <div className="mt-6 border-t pt-5">
            <StageTrack current={m.stage} />
          </div>

          {m.available_actions.length > 0 && (
            <div className="mt-5 flex flex-wrap gap-2 border-t pt-4">
              {m.available_actions.map((action) => (
                <Button
                  key={action.target}
                  size="sm"
                  variant={
                    action.target === 'rejected' || action.target === 'withdrawn'
                      ? 'outline'
                      : 'primary'
                  }
                  onClick={() => setPendingAction(action)}
                >
                  {action.label}
                </Button>
              ))}
            </div>
          )}

          {m.closure_reason && (
            <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 dark:border-red-900 dark:bg-red-950/40">
              <p className="text-[11px] font-semibold text-red-800 dark:text-red-300">Why this ended</p>
              <p className="mt-1 whitespace-pre-line text-xs text-red-700 dark:text-red-300">
                {m.closure_reason}
              </p>
            </div>
          )}
        </CardBody>
      </Card>

      <div className="mb-4 flex gap-1 border-b">
        {TABS.map(({ id: tabId, label, icon: Icon }) => (
          <button
            key={tabId}
            onClick={() => {
              const next = new URLSearchParams(params)
              next.set('tab', tabId)
              setParams(next)
            }}
            className={cn(
              '-mb-px flex items-center gap-1.5 border-b-2 px-3 py-2 text-xs font-medium transition-colors',
              tab === tabId
                ? 'border-brand-500 text-brand-600 dark:text-brand-400'
                : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text)]',
            )}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
            {tabId === 'documents' && m.document_count > 0 && (
              <span className="ml-0.5 rounded-full bg-[var(--surface-sunken)] px-1.5 text-[10px] tabular-nums">
                {m.document_count}
              </span>
            )}
            {tabId === 'reviews' && m.review_count > 0 && (
              <span className="ml-0.5 rounded-full bg-[var(--surface-sunken)] px-1.5 text-[10px] tabular-nums">
                {m.review_count}
              </span>
            )}
          </button>
        ))}
      </div>

      <Card>
        {tab === 'overview' && <OverviewTab monograph={m} />}
        {tab === 'documents' && (
          <DocumentsPanel monographId={id} canUpload={!m.is_finished} canApprove={canApprove} />
        )}
        {tab === 'reviews' && (
          <ReviewsPanel monographId={id} canReview={canReview} isStudent={isStudent} />
        )}
        {tab === 'history' && <Timeline monographId={id} />}
      </Card>

      <TransitionDialog
        monographId={id}
        action={pendingAction}
        onClose={() => setPendingAction(null)}
      />
      <AssignSupervisorDialog
        open={assignOpen}
        onClose={() => setAssignOpen(false)}
        monographId={id}
        departmentId={m.department}
      />
    </>
  )
}

function OverviewTab({ monograph }: { monograph: Monograph }) {
  const sections = [
    { label: 'Abstract', value: monograph.abstract },
    { label: 'Objectives', value: monograph.objectives },
    { label: 'Methodology', value: monograph.methodology },
    { label: 'Expected outcome', value: monograph.expected_outcome },
  ].filter((s) => s.value)

  return (
    <CardBody className="space-y-5">
      {monograph.members.length > 0 && (
        <div>
          <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-subtle">
            Author{monograph.members.length === 1 ? '' : 's'}
          </p>
          <div className="flex flex-wrap gap-2">
            {monograph.members.map((member) => (
              <span
                key={member.id}
                className="rounded-full surface-sunken px-3 py-1 text-xs"
              >
                {member.student.full_name}
                {member.is_lead && <span className="ml-1 text-subtle">· lead</span>}
              </span>
            ))}
          </div>
        </div>
      )}

      {sections.length ? (
        sections.map((section) => (
          <div key={section.label}>
            <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-subtle">
              {section.label}
            </p>
            <p className="whitespace-pre-line text-sm leading-relaxed">{section.value}</p>
          </div>
        ))
      ) : (
        <p className="py-6 text-center text-xs text-muted">
          No details have been written yet.
        </p>
      )}

      {monograph.keywords.length > 0 && (
        <div>
          <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-subtle">Keywords</p>
          <div className="flex flex-wrap gap-1.5">
            {monograph.keywords.map((keyword) => (
              <span key={keyword} className="rounded surface-sunken px-2 py-0.5 text-[11px]">
                {keyword}
              </span>
            ))}
          </div>
        </div>
      )}
    </CardBody>
  )
}

function AssignSupervisorDialog({
  open,
  onClose,
  monographId,
  departmentId,
}: {
  open: boolean
  onClose: () => void
  monographId: string
  departmentId: string
}) {
  const [chosen, setChosen] = useState('')
  const [error, setError] = useState('')
  const queryClient = useQueryClient()

  const { data: supervisors } = useQuery({
    queryKey: ['supervisors', departmentId],
    queryFn: async () => {
      const { data } = await api.get<SupervisorOption[]>(
        `/auth/users/supervisors/?department=${departmentId}`,
      )
      return data
    },
    enabled: open,
  })

  const assign = useMutation({
    mutationFn: () =>
      api.post(`/monographs/${monographId}/assign_supervisor/`, { supervisor_id: chosen }),
    onSuccess: (response) => {
      toast.success(response.data.detail)
      queryClient.invalidateQueries({ queryKey: ['monograph', monographId] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      onClose()
    },
    onError: (e) => setError(errorMessage(e)),
  })

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Assign a supervisor"
      description="Each supervisor's current load is shown so you can spread the work evenly."
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={() => {
              setError('')
              if (!chosen) return setError('Choose a supervisor.')
              assign.mutate()
            }}
            loading={assign.isPending}
          >
            Assign
          </Button>
        </>
      }
    >
      <Select
        label="Supervisor"
        value={chosen}
        onChange={(e) => setChosen(e.target.value)}
        error={error}
        required
      >
        <option value="">Choose someone</option>
        {supervisors?.map((s) => (
          <option key={s.id} value={s.id}>
            {s.display_name} — {s.active_students}
            {s.max_students ? `/${s.max_students}` : ''} students
            {!s.has_capacity ? ' (at capacity)' : ''}
          </option>
        ))}
      </Select>
    </Modal>
  )
}
