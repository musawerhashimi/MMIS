import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, MessageSquare, Plus, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { api, errorMessage } from '@/lib/api'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { Input, Select, Textarea } from '@/components/ui/Input'
import { EmptyState } from '@/components/ui/EmptyState'
import { Skeleton } from '@/components/ui/Skeleton'
import { cn, formatDateTime } from '@/lib/utils'
import type { Review, ReviewDecision } from '@/types'

const DECISION_STYLE: Record<ReviewDecision, string> = {
  approved: 'border-emerald-200 bg-emerald-50 dark:border-emerald-900 dark:bg-emerald-950/30',
  revision_requested: 'border-orange-200 bg-orange-50 dark:border-orange-900 dark:bg-orange-950/30',
  rejected: 'border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950/30',
}

interface Props {
  monographId: string
  canReview: boolean
  isStudent: boolean
}

export function ReviewsPanel({ monographId, canReview, isStudent }: Props) {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['reviews', monographId],
    queryFn: async () => {
      const { data } = await api.get<Review[]>(`/reviews/for_monograph/?monograph=${monographId}`)
      return data
    },
  })

  const resolve = useMutation({
    mutationFn: ({ id, done }: { id: string; done: boolean }) =>
      api.post(`/reviews/comments/${id}/${done ? 'resolve' : 'unresolve'}/`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['reviews', monographId] }),
    onError: (e) => toast.error(errorMessage(e)),
  })

  if (isLoading) {
    return (
      <div className="space-y-3 p-5">
        {Array.from({ length: 2 }).map((_, i) => (
          <Skeleton key={i} className="h-24 w-full" />
        ))}
      </div>
    )
  }

  return (
    <>
      {canReview && (
        <div className="flex justify-end border-b px-5 py-3">
          <Button size="sm" icon={<Plus className="h-3.5 w-3.5" />} onClick={() => setOpen(true)}>
            Write a review
          </Button>
        </div>
      )}

      {!data?.length ? (
        <EmptyState
          icon={<MessageSquare className="h-5 w-5" />}
          title="No feedback yet"
          description={
            canReview
              ? 'Your decisions and comments will be recorded here.'
              : 'Your supervisor has not reviewed your work yet.'
          }
        />
      ) : (
        <div className="space-y-4 p-5">
          {data.map((review) => (
            <div key={review.id} className={cn('rounded-lg border p-4', DECISION_STYLE[review.decision])}>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="text-xs font-semibold">
                    {review.decision_label}
                    <span className="ml-2 font-normal text-muted">round {review.round_number}</span>
                  </p>
                  {review.summary && <p className="mt-1 text-sm font-medium">{review.summary}</p>}
                </div>
                <div className="text-right">
                  <p className="text-[11px] font-medium">{review.reviewer.display_name}</p>
                  <p className="text-[10px] text-muted">{formatDateTime(review.created_at)}</p>
                </div>
              </div>

              {review.document_title && (
                <p className="mt-2 text-[11px] text-muted">
                  On {review.document_title} v{review.document_version_number}
                </p>
              )}

              {review.comments && (
                <p className="mt-3 whitespace-pre-line text-xs leading-relaxed">{review.comments}</p>
              )}

              {review.items.length > 0 && (
                <div className="mt-3 space-y-1.5 border-t pt-3">
                  <p className="text-[10px] font-medium uppercase tracking-wide text-subtle">
                    Corrections ({review.items.filter((i) => i.is_resolved).length} of{' '}
                    {review.items.length} done)
                  </p>
                  {review.items.map((item) => (
                    <div
                      key={item.id}
                      className="flex items-start gap-2 rounded-md bg-[var(--surface-raised)] px-3 py-2"
                    >
                      <button
                        disabled={!isStudent}
                        onClick={() => resolve.mutate({ id: item.id, done: !item.is_resolved })}
                        className={cn(
                          'mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded border transition-colors',
                          item.is_resolved
                            ? 'border-emerald-500 bg-emerald-500 text-white'
                            : 'border-[var(--border-strong)]',
                          isStudent && 'cursor-pointer hover:border-emerald-500',
                        )}
                        aria-label={item.is_resolved ? 'Mark as not done' : 'Mark as done'}
                      >
                        {item.is_resolved && <Check className="h-2.5 w-2.5" />}
                      </button>
                      <div className="min-w-0">
                        {(item.page_number || item.section) && (
                          <p className="text-[10px] font-medium text-subtle">
                            {item.page_number ? `Page ${item.page_number}` : item.section}
                          </p>
                        )}
                        <p
                          className={cn(
                            'text-[11px] leading-relaxed',
                            item.is_resolved && 'text-subtle line-through',
                          )}
                        >
                          {item.body}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <ReviewDialog open={open} onClose={() => setOpen(false)} monographId={monographId} />
    </>
  )
}

interface Correction {
  page_number: string
  body: string
}

function ReviewDialog({
  open,
  onClose,
  monographId,
}: {
  open: boolean
  onClose: () => void
  monographId: string
}) {
  const [decision, setDecision] = useState<ReviewDecision>('revision_requested')
  const [summary, setSummary] = useState('')
  const [comments, setComments] = useState('')
  const [items, setItems] = useState<Correction[]>([])
  const [error, setError] = useState('')
  const queryClient = useQueryClient()

  const submit = useMutation({
    mutationFn: async () => {
      const { data } = await api.post('/reviews/', {
        monograph: monographId,
        decision,
        summary,
        comments,
        items: items
          .filter((i) => i.body.trim())
          .map((i) => ({
            page_number: i.page_number ? Number(i.page_number) : null,
            body: i.body,
          })),
      })
      return data
    },
    onSuccess: (data) => {
      toast.success('Review recorded', {
        description: data.moved_to ? `Monograph moved to: ${data.moved_to}` : undefined,
      })
      queryClient.invalidateQueries({ queryKey: ['reviews', monographId] })
      queryClient.invalidateQueries({ queryKey: ['monograph', monographId] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      reset()
      onClose()
    },
    onError: (e) => setError(errorMessage(e)),
  })

  function reset() {
    setSummary('')
    setComments('')
    setItems([])
    setError('')
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Write a review"
      description="Your decision moves the monograph and is shown to the student immediately."
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={() => submit.mutate()} loading={submit.isPending}>
            Submit review
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Select
          label="Decision"
          value={decision}
          onChange={(e) => setDecision(e.target.value as ReviewDecision)}
          required
        >
          <option value="approved">Approve — the work is satisfactory</option>
          <option value="revision_requested">Request revisions — changes are needed</option>
          <option value="rejected">Reject</option>
        </Select>

        <Input
          label="Summary"
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
          placeholder="The one line the student sees first"
        />

        <Textarea
          label="Comments"
          required={decision === 'revision_requested'}
          value={comments}
          onChange={(e) => setComments(e.target.value)}
          rows={5}
          placeholder="Explain what is good and what must change."
        />

        <div>
          <div className="mb-2 flex items-center justify-between">
            <label className="text-xs font-medium">Specific corrections</label>
            <Button
              variant="ghost"
              size="sm"
              icon={<Plus className="h-3 w-3" />}
              onClick={() => setItems([...items, { page_number: '', body: '' }])}
            >
              Add
            </Button>
          </div>
          <p className="mb-2 text-[11px] text-subtle">
            Pin a correction to a page so the student can work through them one by one.
          </p>

          <div className="space-y-2">
            {items.map((item, index) => (
              <div key={index} className="flex gap-2">
                <input
                  type="number"
                  min={1}
                  value={item.page_number}
                  onChange={(e) => {
                    const next = [...items]
                    next[index].page_number = e.target.value
                    setItems(next)
                  }}
                  placeholder="Page"
                  className="h-9 w-20 rounded-lg border bg-[var(--surface)] px-2 text-xs outline-none focus:border-brand-500"
                />
                <input
                  value={item.body}
                  onChange={(e) => {
                    const next = [...items]
                    next[index].body = e.target.value
                    setItems(next)
                  }}
                  placeholder="What needs to change here"
                  className="h-9 flex-1 rounded-lg border bg-[var(--surface)] px-3 text-xs outline-none focus:border-brand-500"
                />
                <button
                  onClick={() => setItems(items.filter((_, i) => i !== index))}
                  className="rounded-lg px-2 text-[var(--text-muted)] hover:bg-[var(--surface-sunken)]"
                  aria-label="Remove correction"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        </div>

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300">
            {error}
          </div>
        )}
      </div>
    </Modal>
  )
}
