import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { BookOpen, Filter, PlusCircle, Search, X } from 'lucide-react'
import { api } from '@/lib/api'
import { useAuth } from '@/stores/auth'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Select } from '@/components/ui/Input'
import { StageBadge } from '@/components/ui/Badge'
import { EmptyState } from '@/components/ui/EmptyState'
import { TableSkeleton } from '@/components/ui/Skeleton'
import { ProgressRing } from '@/components/charts/ProgressRing'
import { cn, STAGE_COLOR, waitSeverity } from '@/lib/utils'
import type { MonographListItem, Paginated } from '@/types'

const STAGES: { value: string; label: string }[] = [
  { value: 'draft', label: 'Draft' },
  { value: 'topic_submitted', label: 'Topic Submitted' },
  { value: 'topic_approved', label: 'Topic Approved' },
  { value: 'proposal_submitted', label: 'Proposal Submitted' },
  { value: 'under_review', label: 'Under Review' },
  { value: 'revision_required', label: 'Revision Required' },
  { value: 'proposal_approved', label: 'Proposal Approved' },
  { value: 'research_in_progress', label: 'Research In Progress' },
  { value: 'final_submission', label: 'Final Submission' },
  { value: 'final_review', label: 'Final Review' },
  { value: 'defense_scheduled', label: 'Defense Scheduled' },
  { value: 'defended', label: 'Defended' },
  { value: 'completed', label: 'Completed' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'withdrawn', label: 'Withdrawn' },
]

const WAIT_TONE = {
  ok: 'text-[var(--text-muted)]',
  warn: 'text-amber-600 dark:text-amber-400',
  late: 'text-red-600 dark:text-red-400 font-semibold',
}

/**
 * Every monograph this person may see.
 *
 * Filters live in the URL so a head of department can bookmark "everyone who
 * is stuck" or send that link to a colleague.
 */
export function MonographListPage() {
  const user = useAuth((s) => s.user)
  const [params, setParams] = useSearchParams()
  const [search, setSearch] = useState(params.get('search') ?? '')

  const query = params.toString()

  const { data, isLoading } = useQuery({
    queryKey: ['monographs', query],
    queryFn: async () => {
      const { data } = await api.get<Paginated<MonographListItem>>(`/monographs/?${query}`)
      return data
    },
  })

  function setParam(key: string, value: string) {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    next.delete('page')
    setParams(next)
  }

  function submitSearch(event: React.FormEvent) {
    event.preventDefault()
    setParam('search', search.trim())
  }

  const activeFilters = ['stage', 'active', 'unassigned', 'stuck_days', 'search'].filter((key) =>
    params.get(key),
  )

  return (
    <>
      <PageHeader
        title="Monographs"
        description={
          user?.permissions.is_student
            ? 'Your monograph and its history.'
            : 'Everything in your department, with where each one stands.'
        }
        action={
          user?.permissions.is_student ? (
            <Link to="/monographs/new">
              <Button icon={<PlusCircle className="h-4 w-4" />}>Propose a topic</Button>
            </Link>
          ) : undefined
        }
      />

      <Card className="mb-4 p-3">
        <div className="flex flex-wrap items-end gap-3">
          <form onSubmit={submitSearch} className="min-w-[200px] flex-1">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-subtle" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by title or keyword"
                className="h-9.5 w-full rounded-lg border bg-[var(--surface)] pl-9 pr-3 text-sm outline-none focus:border-brand-500"
              />
            </div>
          </form>

          <div className="w-44">
            <Select
              value={params.get('stage') ?? ''}
              onChange={(e) => setParam('stage', e.target.value)}
              aria-label="Filter by stage"
            >
              <option value="">All stages</option>
              {STAGES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </Select>
          </div>

          <div className="w-40">
            <Select
              value={params.get('active') ?? ''}
              onChange={(e) => setParam('active', e.target.value)}
              aria-label="Filter by status"
            >
              <option value="">Active and finished</option>
              <option value="true">Active only</option>
              <option value="false">Finished only</option>
            </Select>
          </div>

          {activeFilters.length > 0 && (
            <Button
              variant="ghost"
              size="sm"
              icon={<X className="h-3.5 w-3.5" />}
              onClick={() => {
                setSearch('')
                setParams(new URLSearchParams())
              }}
            >
              Clear
            </Button>
          )}
        </div>
      </Card>

      {isLoading ? (
        <TableSkeleton rows={6} />
      ) : !data?.results.length ? (
        <Card>
          <EmptyState
            icon={<BookOpen className="h-5 w-5" />}
            title={activeFilters.length ? 'Nothing matches those filters' : 'No monographs yet'}
            description={
              activeFilters.length
                ? 'Try widening your search.'
                : 'Monographs will appear here once students propose their topics.'
            }
            action={
              activeFilters.length ? (
                <Button variant="secondary" size="sm" onClick={() => setParams(new URLSearchParams())}>
                  Clear filters
                </Button>
              ) : undefined
            }
          />
        </Card>
      ) : (
        <>
          <p className="mb-3 flex items-center gap-1.5 text-xs text-muted">
            <Filter className="h-3.5 w-3.5" />
            {data.count} monograph{data.count === 1 ? '' : 's'}
          </p>

          <div className="space-y-2">
            {data.results.map((m) => {
              const tone = waitSeverity(m.days_in_current_stage)
              return (
                <Link key={m.id} to={`/monographs/${m.id}`}>
                  <Card className="flex items-center gap-4 p-4 transition-shadow hover:shadow-md">
                    <ProgressRing
                      value={m.progress_percent}
                      size={52}
                      thickness={5}
                      color={STAGE_COLOR[m.stage]}
                    />

                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">{m.title}</p>
                      <p className="mt-0.5 truncate text-xs text-muted">
                        {m.student_names.join(', ') || 'No author'}
                        {m.supervisor_name && ` · supervised by ${m.supervisor_name}`}
                      </p>
                      <div className="mt-2 flex flex-wrap items-center gap-2">
                        <StageBadge stage={m.stage} label={m.stage_label} size="sm" />
                        {!m.supervisor_name && !m.is_finished && (
                          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-800 dark:bg-amber-950 dark:text-amber-300">
                            No supervisor
                          </span>
                        )}
                        {m.research_area_name && (
                          <span className="text-[11px] text-subtle">{m.research_area_name}</span>
                        )}
                      </div>
                    </div>

                    <div className="hidden shrink-0 text-right sm:block">
                      {m.final_grade ? (
                        <>
                          <p className="text-lg font-semibold tabular-nums">{m.final_grade}</p>
                          <p className="text-[10px] text-subtle">final grade</p>
                        </>
                      ) : (
                        <>
                          <p className={cn('text-sm tabular-nums', WAIT_TONE[tone])}>
                            {m.days_in_current_stage}d
                          </p>
                          <p className="text-[10px] text-subtle">at this stage</p>
                        </>
                      )}
                    </div>
                  </Card>
                </Link>
              )
            })}
          </div>

          {data.pages > 1 && (
            <div className="mt-4 flex items-center justify-between">
              <p className="text-xs text-muted">
                Page {data.page} of {data.pages}
              </p>
              <div className="flex gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={!data.previous}
                  onClick={() => setParam('page', String(data.page - 1))}
                >
                  Previous
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={!data.next}
                  onClick={() => setParam('page', String(data.page + 1))}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </>
  )
}
