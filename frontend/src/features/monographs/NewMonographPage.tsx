import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { ArrowLeft, Info } from 'lucide-react'
import { toast } from 'sonner'
import { api, errorMessage, fieldErrors } from '@/lib/api'
import { useAuth } from '@/stores/auth'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card, CardBody } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input, Select, Textarea } from '@/components/ui/Input'
import type { AcademicYearOption, ResearchAreaOption } from './types'

/**
 * Proposing a topic.
 *
 * Saved as a draft, which the student can keep editing until they formally
 * submit it — so nothing is locked in by pressing the wrong button early.
 */
export function NewMonographPage() {
  const user = useAuth((s) => s.user)
  const navigate = useNavigate()

  const [form, setForm] = useState({
    title: '',
    abstract: '',
    objectives: '',
    methodology: '',
    expected_outcome: '',
    research_area: '',
  })
  const [errors, setErrors] = useState<Record<string, string>>({})

  const { data: year } = useQuery({
    queryKey: ['academic-year', 'current'],
    queryFn: async () => {
      const { data } = await api.get<AcademicYearOption | null>(
        '/organization/academic-years/current/',
      )
      return data
    },
  })

  const { data: areas } = useQuery({
    queryKey: ['research-areas', user?.department],
    queryFn: async () => {
      const { data } = await api.get<{ results: ResearchAreaOption[] }>(
        `/organization/research-areas/?department=${user?.department}`,
      )
      return data.results
    },
    enabled: Boolean(user?.department),
  })

  const create = useMutation({
    mutationFn: async () => {
      const { data } = await api.post('/monographs/', {
        ...form,
        research_area: form.research_area || null,
        department: user?.department,
        academic_year: year?.id,
      })
      return data
    },
    onSuccess: (data) => {
      toast.success('Your topic has been saved as a draft', {
        description: 'You can keep editing it until you submit it for approval.',
      })
      navigate(`/monographs/${data.id}`)
    },
    onError: (error) => {
      setErrors(fieldErrors(error))
      toast.error(errorMessage(error))
    },
  })

  function set(key: keyof typeof form, value: string) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  function submit(event: React.FormEvent) {
    event.preventDefault()
    setErrors({})
    if (!form.title.trim()) {
      setErrors({ title: 'Give your monograph a working title.' })
      return
    }
    create.mutate()
  }

  if (!user?.department) {
    return (
      <Card>
        <CardBody>
          <p className="py-6 text-center text-sm text-muted">
            Your account is not attached to a department yet. Ask the administrator to set this
            up before proposing a topic.
          </p>
        </CardBody>
      </Card>
    )
  }

  return (
    <>
      <PageHeader
        breadcrumb={
          <Link to="/monographs" className="inline-flex items-center gap-1 hover:underline">
            <ArrowLeft className="h-3 w-3" /> All monographs
          </Link>
        }
        title="Propose a topic"
        description="Nothing here is final. You can change everything until you submit it."
      />

      <form onSubmit={submit}>
        <Card>
          <CardBody className="space-y-5">
            <div className="flex items-start gap-2 rounded-lg surface-sunken px-3 py-2.5">
              <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-subtle" />
              <p className="text-[11px] leading-relaxed text-muted">
                Saved as a draft. When you are happy with it, open the monograph and choose
                <strong className="font-medium"> Topic submitted for approval</strong> — only then
                does the department see it.
              </p>
            </div>

            <Input
              id="title"
              label="Working title"
              required
              value={form.title}
              onChange={(e) => set('title', e.target.value)}
              error={errors.title}
              placeholder="What is your monograph about?"
            />

            <Select
              id="research_area"
              label="Research area"
              value={form.research_area}
              onChange={(e) => set('research_area', e.target.value)}
              error={errors.research_area}
              hint="Needed before you can submit the topic for approval."
            >
              <option value="">Choose an area</option>
              {areas?.map((area) => (
                <option key={area.id} value={area.id}>
                  {area.name}
                </option>
              ))}
            </Select>

            <Textarea
              id="abstract"
              label="Abstract"
              value={form.abstract}
              onChange={(e) => set('abstract', e.target.value)}
              error={errors.abstract}
              rows={4}
              hint="A short description of the problem and why it matters."
            />

            <Textarea
              id="objectives"
              label="Objectives"
              value={form.objectives}
              onChange={(e) => set('objectives', e.target.value)}
              rows={3}
              hint="What do you want to achieve?"
            />

            <Textarea
              id="methodology"
              label="Methodology"
              value={form.methodology}
              onChange={(e) => set('methodology', e.target.value)}
              rows={3}
              hint="How will you do the work?"
            />

            <Textarea
              id="expected_outcome"
              label="Expected outcome"
              value={form.expected_outcome}
              onChange={(e) => set('expected_outcome', e.target.value)}
              rows={2}
            />
          </CardBody>

          <div className="flex justify-end gap-2 border-t px-5 py-4">
            <Link to="/monographs">
              <Button variant="secondary" type="button">
                Cancel
              </Button>
            </Link>
            <Button type="submit" loading={create.isPending}>
              Save draft
            </Button>
          </div>
        </Card>
      </form>
    </>
  )
}
