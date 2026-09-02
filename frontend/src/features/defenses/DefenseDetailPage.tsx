import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft, BookOpenCheck, CalendarClock, MapPin, Printer, Users,
} from 'lucide-react'
import { toast } from 'sonner'
import { api, errorMessage } from '@/lib/api'
import { useAuth } from '@/stores/auth'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { Badge } from '@/components/ui/Badge'
import { Input, Select, Textarea } from '@/components/ui/Input'
import { CardSkeleton } from '@/components/ui/Skeleton'
import { formatDateTime } from '@/lib/utils'
import type { Defense } from '@/types'

const RESULT_STYLE: Record<string, string> = {
  passed: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300',
  passed_with_revisions: 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300',
  failed: 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300',
}

export function DefenseDetailPage() {
  const { id = '' } = useParams()
  const user = useAuth((s) => s.user)
  const queryClient = useQueryClient()
  const [scoreOpen, setScoreOpen] = useState(false)
  const [resultOpen, setResultOpen] = useState(false)

  const { data: defense, isLoading } = useQuery({
    queryKey: ['defense', id],
    queryFn: async () => {
      const { data } = await api.get<Defense>(`/defenses/${id}/`)
      return data
    },
  })

  const markRead = useMutation({
    mutationFn: () => api.post(`/defenses/${id}/mark_read/`),
    onSuccess: () => {
      toast.success('Marked as read')
      queryClient.invalidateQueries({ queryKey: ['defense', id] })
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  if (isLoading || !defense) {
    return (
      <>
        <PageHeader title="Loading" />
        <CardSkeleton rows={5} />
      </>
    )
  }

  const mySeat = defense.committee.find((c) => c.member.id === user?.id)
  const canRecord = user?.permissions.is_head_of_department || user?.permissions.is_admin

  return (
    <>
      <PageHeader
        breadcrumb={
          <Link to="/defenses" className="inline-flex items-center gap-1 hover:underline">
            <ArrowLeft className="h-3 w-3" /> All defenses
          </Link>
        }
        title={defense.monograph_title}
        description={defense.student_names.join(', ')}
        action={
          <div className="flex gap-2">
            <Link to={`/monographs/${defense.monograph}/forms`}>
              <Button variant="secondary" size="sm" icon={<Printer className="h-3.5 w-3.5" />}>
                Forms
              </Button>
            </Link>
            {canRecord && !defense.result && (
              <Button size="sm" onClick={() => setResultOpen(true)}>
                Record the result
              </Button>
            )}
          </div>
        }
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader
            title="Committee"
            description={
              defense.all_scores_in
                ? 'Every score is in.'
                : `${defense.committee.filter((c) => c.score != null).length} of ${defense.committee.length} have scored.`
            }
            action={<Users className="h-4 w-4 text-subtle" />}
          />
          <CardBody className="p-0">
            <div className="divide-y">
              {defense.committee.map((seat) => (
                <div key={seat.id} className="flex items-center gap-3 px-5 py-3">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium">{seat.member.display_name}</p>
                    <p className="mt-0.5 text-[11px] text-muted">{seat.role_label}</p>
                  </div>

                  {seat.has_read_monograph && (
                    <span
                      className="inline-flex items-center gap-1 text-[10px] text-emerald-600 dark:text-emerald-400"
                      title="Has read the monograph"
                    >
                      <BookOpenCheck className="h-3 w-3" /> read
                    </span>
                  )}

                  <span className="w-16 shrink-0 text-right">
                    {seat.score != null ? (
                      <span className="text-sm font-semibold tabular-nums">{seat.score}</span>
                    ) : (
                      <span className="text-[11px] text-subtle">not scored</span>
                    )}
                  </span>
                </div>
              ))}
            </div>

            {mySeat && (
              <div className="flex flex-wrap gap-2 border-t px-5 py-3">
                {!mySeat.has_read_monograph && (
                  <Button
                    variant="secondary"
                    size="sm"
                    loading={markRead.isPending}
                    onClick={() => markRead.mutate()}
                    icon={<BookOpenCheck className="h-3.5 w-3.5" />}
                  >
                    I have read it
                  </Button>
                )}
                <Button size="sm" onClick={() => setScoreOpen(true)}>
                  {mySeat.score != null ? 'Change my score' : 'Enter my score'}
                </Button>
              </div>
            )}
          </CardBody>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader title="When and where" />
            <CardBody className="space-y-2 text-xs">
              <p className="inline-flex items-center gap-1.5">
                <CalendarClock className="h-3.5 w-3.5 text-subtle" />
                {formatDateTime(defense.scheduled_at)}
              </p>
              <p className="inline-flex items-center gap-1.5">
                <MapPin className="h-3.5 w-3.5 text-subtle" />
                {defense.location || 'Location to be confirmed'}
              </p>
              <p className="text-subtle">{defense.duration_minutes} minutes</p>
            </CardBody>
          </Card>

          {(defense.result || defense.final_grade) && (
            <Card>
              <CardHeader title="Result" />
              <CardBody className="space-y-3">
                {defense.result && (
                  <Badge className={RESULT_STYLE[defense.result] ?? ''}>{defense.result_label}</Badge>
                )}

                <dl className="space-y-1.5 text-xs">
                  <div className="flex justify-between">
                    <dt className="text-subtle">Committee average</dt>
                    <dd className="font-medium tabular-nums">{defense.committee_average ?? '—'}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-subtle">Supervisor</dt>
                    <dd className="font-medium tabular-nums">{defense.supervisor_score ?? '—'}</dd>
                  </div>
                  <div className="flex justify-between border-t pt-1.5">
                    <dt className="font-medium">Final grade</dt>
                    <dd className="text-base font-semibold tabular-nums">
                      {defense.final_grade ?? '—'}
                    </dd>
                  </div>
                </dl>

                {defense.required_revisions && (
                  <div className="rounded-lg surface-sunken p-3">
                    <p className="text-[10px] font-medium uppercase tracking-wide text-subtle">
                      Required revisions
                    </p>
                    <p className="mt-1 whitespace-pre-line text-[11px]">
                      {defense.required_revisions}
                    </p>
                    {defense.revisions_due_date && (
                      <p className="mt-1.5 text-[11px] font-medium">
                        Due by {defense.revisions_due_date}
                      </p>
                    )}
                  </div>
                )}

                {defense.notes && (
                  <div>
                    <p className="text-[10px] font-medium uppercase tracking-wide text-subtle">
                      Remarks
                    </p>
                    <p className="mt-1 whitespace-pre-line text-[11px]">{defense.notes}</p>
                  </div>
                )}
              </CardBody>
            </Card>
          )}
        </div>
      </div>

      <ScoreDialog
        open={scoreOpen}
        onClose={() => setScoreOpen(false)}
        defenseId={id}
        current={mySeat?.score ?? ''}
      />
      <ResultDialog
        open={resultOpen}
        onClose={() => setResultOpen(false)}
        defense={defense}
      />
    </>
  )
}

function ScoreDialog({
  open,
  onClose,
  defenseId,
  current,
}: {
  open: boolean
  onClose: () => void
  defenseId: string
  current: string
}) {
  const [score, setScore] = useState(current)
  const [comments, setComments] = useState('')
  const [error, setError] = useState('')
  const queryClient = useQueryClient()

  const save = useMutation({
    mutationFn: () => api.post(`/defenses/${defenseId}/score/`, { score, comments }),
    onSuccess: (response) => {
      toast.success('Score recorded', {
        description: response.data.all_scores_in
          ? 'Every committee member has now scored.'
          : undefined,
      })
      queryClient.invalidateQueries({ queryKey: ['defense', defenseId] })
      onClose()
    },
    onError: (e) => setError(errorMessage(e)),
  })

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Enter your score"
      description="Only you can enter your own score."
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={() => {
              setError('')
              const value = Number(score)
              if (!score || Number.isNaN(value) || value < 0 || value > 100) {
                return setError('Enter a score between 0 and 100.')
              }
              save.mutate()
            }}
            loading={save.isPending}
          >
            Save
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Input
          label="Score out of 100"
          type="number"
          min={0}
          max={100}
          step="0.01"
          required
          value={score}
          onChange={(e) => setScore(e.target.value)}
          error={error}
        />
        <Textarea
          label="Comments (optional)"
          value={comments}
          onChange={(e) => setComments(e.target.value)}
          rows={4}
        />
      </div>
    </Modal>
  )
}

function ResultDialog({
  open,
  onClose,
  defense,
}: {
  open: boolean
  onClose: () => void
  defense: Defense
}) {
  const [result, setResult] = useState('passed')
  const [supervisorScore, setSupervisorScore] = useState('')
  const [notes, setNotes] = useState('')
  const [revisions, setRevisions] = useState('')
  const [dueDate, setDueDate] = useState('')
  const [error, setError] = useState('')
  const queryClient = useQueryClient()

  const record = useMutation({
    mutationFn: () =>
      api.post(`/defenses/${defense.id}/record_result/`, {
        result,
        supervisor_score: supervisorScore || null,
        notes,
        required_revisions: revisions,
        revisions_due_date: dueDate || null,
      }),
    onSuccess: (response) => {
      toast.success('Result recorded', {
        description: `Final grade: ${response.data.final_grade}`,
      })
      queryClient.invalidateQueries({ queryKey: ['defense', defense.id] })
      queryClient.invalidateQueries({ queryKey: ['monograph', defense.monograph] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      onClose()
    },
    onError: (e) => setError(errorMessage(e)),
  })

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Record the result"
      description="The final grade is worked out from your department's own weights."
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={() => record.mutate()} loading={record.isPending}>
            Record
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        {!defense.all_scores_in && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-800 dark:bg-amber-950/50 dark:text-amber-200">
            Not every committee member has scored yet. The result cannot be recorded until they
            have.
          </div>
        )}

        <Select label="Result" required value={result} onChange={(e) => setResult(e.target.value)}>
          <option value="passed">Passed</option>
          <option value="passed_with_revisions">Passed with minor revisions</option>
          <option value="failed">Failed</option>
        </Select>

        <Input
          label="Supervisor's assessment"
          type="number"
          min={0}
          max={100}
          step="0.01"
          value={supervisorScore}
          onChange={(e) => setSupervisorScore(e.target.value)}
          hint={`Committee average is ${defense.committee_average ?? 'not yet available'}.`}
        />

        {result === 'passed_with_revisions' && (
          <>
            <Textarea
              label="Required revisions"
              value={revisions}
              onChange={(e) => setRevisions(e.target.value)}
              rows={3}
            />
            <Input
              label="Revisions due by"
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
            />
          </>
        )}

        <Textarea
          label="Committee remarks"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={3}
        />

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300">
            {error}
          </div>
        )}
      </div>
    </Modal>
  )
}
