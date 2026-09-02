import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Archive, Download, Search, User } from 'lucide-react'
import { toast } from 'sonner'
import { api, errorMessage, tokens } from '@/lib/api'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card, CardBody } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Select } from '@/components/ui/Input'
import { EmptyState } from '@/components/ui/EmptyState'
import { TableSkeleton } from '@/components/ui/Skeleton'
import { formatDate } from '@/lib/utils'
import type { Paginated } from '@/types'

interface ArchiveEntry {
  id: string
  monograph: string
  title: string
  abstract: string
  keywords: string[]
  author_names: string[]
  supervisor_name: string
  department_name: string
  academic_year_name: string
  research_area_name: string
  final_grade: string | null
  defended_on: string | null
  is_public: boolean
  view_count: number
  download_url: string | null
}

/**
 * The department's permanent library.
 *
 * This is the thing that did not exist before: past monographs future
 * students can search and read, instead of starting from nothing each year.
 */
export function ArchivePage() {
  const [params, setParams] = useSearchParams()
  const [search, setSearch] = useState(params.get('search') ?? '')

  const { data, isLoading } = useQuery({
    queryKey: ['archive', params.toString()],
    queryFn: async () => {
      const { data } = await api.get<Paginated<ArchiveEntry>>(`/archive/?${params.toString()}`)
      return data
    },
  })

  const { data: years } = useQuery({
    queryKey: ['archive', 'years'],
    queryFn: async () => {
      const { data } = await api.get<string[]>('/archive/years/')
      return data
    },
  })

  const { data: areas } = useQuery({
    queryKey: ['archive', 'areas'],
    queryFn: async () => {
      const { data } = await api.get<string[]>('/archive/areas/')
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

  async function download(url: string, title: string) {
    try {
      const response = await fetch(url, {
        headers: { Authorization: `Bearer ${tokens.access}` },
      })
      if (!response.ok) throw new Error('You cannot open this file.')
      const blob = await response.blob()
      const objectUrl = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = objectUrl
      link.download = `${title.slice(0, 60)}.pdf`
      link.click()
      URL.revokeObjectURL(objectUrl)
    } catch (error) {
      toast.error(errorMessage(error))
    }
  }

  return (
    <>
      <PageHeader
        title="Archive"
        description="Every finished monograph the department has produced, searchable."
      />

      <Card className="mb-4 p-3">
        <div className="flex flex-wrap items-end gap-3">
          <form
            onSubmit={(e) => {
              e.preventDefault()
              setParam('search', search.trim())
            }}
            className="min-w-[200px] flex-1"
          >
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-subtle" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by title, author, supervisor or keyword"
                className="h-9.5 w-full rounded-lg border bg-[var(--surface)] pl-9 pr-3 text-sm outline-none focus:border-brand-500"
              />
            </div>
          </form>

          <div className="w-40">
            <Select
              value={params.get('academic_year_name') ?? ''}
              onChange={(e) => setParam('academic_year_name', e.target.value)}
              aria-label="Filter by year"
            >
              <option value="">All years</option>
              {years?.map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </Select>
          </div>

          <div className="w-48">
            <Select
              value={params.get('research_area_name') ?? ''}
              onChange={(e) => setParam('research_area_name', e.target.value)}
              aria-label="Filter by research area"
            >
              <option value="">All research areas</option>
              {areas?.map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </Select>
          </div>
        </div>
      </Card>

      {isLoading ? (
        <TableSkeleton rows={5} />
      ) : !data?.results.length ? (
        <Card>
          <EmptyState
            icon={<Archive className="h-5 w-5" />}
            title="Nothing archived yet"
            description="Monographs are added here once they are defended and completed."
          />
        </Card>
      ) : (
        <>
          <p className="mb-3 text-xs text-muted">
            {data.count} monograph{data.count === 1 ? '' : 's'}
          </p>
          <div className="space-y-2">
            {data.results.map((entry) => (
              <Card key={entry.id}>
                <CardBody>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <h3 className="text-sm font-medium leading-snug">{entry.title}</h3>
                      <p className="mt-1 inline-flex items-center gap-1 text-[11px] text-muted">
                        <User className="h-3 w-3" />
                        {entry.author_names.join(', ')}
                        {entry.supervisor_name && ` · supervised by ${entry.supervisor_name}`}
                      </p>
                      {entry.abstract && (
                        <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-muted">
                          {entry.abstract}
                        </p>
                      )}
                      <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-subtle">
                        <span>{entry.academic_year_name}</span>
                        {entry.research_area_name && <span>· {entry.research_area_name}</span>}
                        {entry.defended_on && <span>· defended {formatDate(entry.defended_on)}</span>}
                      </div>
                    </div>

                    <div className="shrink-0 text-right">
                      {entry.final_grade && (
                        <>
                          <p className="text-lg font-semibold tabular-nums">{entry.final_grade}</p>
                          <p className="text-[10px] text-subtle">final grade</p>
                        </>
                      )}
                      {entry.download_url && (
                        <Button
                          variant="secondary"
                          size="sm"
                          className="mt-2"
                          icon={<Download className="h-3.5 w-3.5" />}
                          onClick={() => download(entry.download_url!, entry.title)}
                        >
                          Read
                        </Button>
                      )}
                    </div>
                  </div>
                </CardBody>
              </Card>
            ))}
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
