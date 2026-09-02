import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Save, Settings2 } from 'lucide-react'
import { toast } from 'sonner'
import { api, errorMessage, fieldErrors } from '@/lib/api'
import { useAuth } from '@/stores/auth'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input, Select } from '@/components/ui/Input'
import { CardSkeleton } from '@/components/ui/Skeleton'

interface Policy {
  id: string
  topic_approval_mode: string
  topic_approval_votes_required: number
  supervisor_assignment_mode: string
  default_max_students_per_supervisor: number
  allow_group_monographs: boolean
  max_students_per_monograph: number
  committee_size: number
  supervisor_grade_weight: number
  committee_grade_weight: number
  passing_grade: string
  use_fixed_stage_deadlines: boolean
  supervisor_response_days: number
  student_inactivity_days: number
  similarity_threshold: number
}

/**
 * How this department runs its process.
 *
 * Every field here answers a question that turned out to differ between
 * departments. Changing them is data entry, never a code change.
 */
export function SettingsPage() {
  const user = useAuth((s) => s.user)
  const departmentId = user?.department
  const queryClient = useQueryClient()

  const [form, setForm] = useState<Policy | null>(null)
  const [errors, setErrors] = useState<Record<string, string>>({})

  const { data, isLoading } = useQuery({
    queryKey: ['policy', departmentId],
    queryFn: async () => {
      const { data } = await api.get<Policy>(`/organization/departments/${departmentId}/policy/`)
      return data
    },
    enabled: Boolean(departmentId),
  })

  useEffect(() => {
    if (data) setForm(data)
  }, [data])

  const save = useMutation({
    mutationFn: () =>
      api.patch(`/organization/departments/${departmentId}/policy/`, form),
    onSuccess: () => {
      toast.success('Settings saved')
      queryClient.invalidateQueries({ queryKey: ['policy', departmentId] })
      setErrors({})
    },
    onError: (error) => {
      setErrors(fieldErrors(error))
      toast.error(errorMessage(error))
    },
  })

  function set<K extends keyof Policy>(key: K, value: Policy[K]) {
    setForm((f) => (f ? { ...f, [key]: value } : f))
  }

  if (!departmentId) {
    return (
      <Card>
        <CardBody>
          <p className="py-6 text-center text-sm text-muted">
            Your account is not attached to a department.
          </p>
        </CardBody>
      </Card>
    )
  }

  if (isLoading || !form) {
    return (
      <>
        <PageHeader title="Settings" />
        <CardSkeleton rows={6} />
      </>
    )
  }

  const weightsOk = form.supervisor_grade_weight + form.committee_grade_weight === 100

  return (
    <>
      <PageHeader
        title="Department settings"
        description="The rules your department follows. Confirm these with your department head before changing them."
        action={
          <Button
            icon={<Save className="h-4 w-4" />}
            loading={save.isPending}
            disabled={!weightsOk}
            onClick={() => save.mutate()}
          >
            Save changes
          </Button>
        }
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader
            title="Approving topics"
            description="Who decides whether a proposed topic goes ahead"
            action={<Settings2 className="h-4 w-4 text-subtle" />}
          />
          <CardBody className="space-y-4">
            <Select
              label="How topics are approved"
              value={form.topic_approval_mode}
              onChange={(e) => set('topic_approval_mode', e.target.value)}
            >
              <option value="head_only">The head of department decides alone</option>
              <option value="committee_vote">A committee votes</option>
            </Select>

            {form.topic_approval_mode === 'committee_vote' && (
              <Input
                label="Approvals needed"
                type="number"
                min={1}
                value={form.topic_approval_votes_required}
                onChange={(e) => set('topic_approval_votes_required', Number(e.target.value))}
              />
            )}

            <Select
              label="How supervisors are chosen"
              value={form.supervisor_assignment_mode}
              onChange={(e) => set('supervisor_assignment_mode', e.target.value)}
            >
              <option value="assigned_by_head">Assigned by the head of department</option>
              <option value="student_chooses">The student chooses, the head confirms</option>
              <option value="student_preference">The student ranks preferences, the head decides</option>
            </Select>
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Workload" description="How many students one supervisor may carry" />
          <CardBody className="space-y-4">
            <Input
              label="Students per supervisor"
              type="number"
              min={1}
              value={form.default_max_students_per_supervisor}
              onChange={(e) =>
                set('default_max_students_per_supervisor', Number(e.target.value))
              }
              hint="An individual supervisor's limit can be set separately on their profile."
            />

            <Select
              label="Group monographs"
              value={form.allow_group_monographs ? 'yes' : 'no'}
              onChange={(e) => set('allow_group_monographs', e.target.value === 'yes')}
            >
              <option value="yes">Students may write together</option>
              <option value="no">One student per monograph</option>
            </Select>

            {form.allow_group_monographs && (
              <Input
                label="Most students on one monograph"
                type="number"
                min={1}
                max={6}
                value={form.max_students_per_monograph}
                onChange={(e) => set('max_students_per_monograph', Number(e.target.value))}
              />
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Defense and grading" description="How the final grade is worked out" />
          <CardBody className="space-y-4">
            <Input
              label="Committee size"
              type="number"
              min={1}
              max={10}
              value={form.committee_size}
              onChange={(e) => set('committee_size', Number(e.target.value))}
              hint="A defense cannot be scheduled with fewer members than this."
            />

            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                label="Supervisor weight (%)"
                type="number"
                min={0}
                max={100}
                value={form.supervisor_grade_weight}
                onChange={(e) => set('supervisor_grade_weight', Number(e.target.value))}
                error={errors.supervisor_grade_weight}
              />
              <Input
                label="Committee weight (%)"
                type="number"
                min={0}
                max={100}
                value={form.committee_grade_weight}
                onChange={(e) => set('committee_grade_weight', Number(e.target.value))}
              />
            </div>

            {!weightsOk && (
              <p className="text-[11px] text-red-600 dark:text-red-400">
                The two weights must add up to 100 — they currently total{' '}
                {form.supervisor_grade_weight + form.committee_grade_weight}.
              </p>
            )}

            <Input
              label="Passing grade"
              type="number"
              min={0}
              max={100}
              step="0.01"
              value={form.passing_grade}
              onChange={(e) => set('passing_grade', e.target.value)}
            />
          </CardBody>
        </Card>

        <Card>
          <CardHeader
            title="Deadlines and warnings"
            description="When the system should raise the alarm"
          />
          <CardBody className="space-y-4">
            <Input
              label="Supervisor response time (days)"
              type="number"
              min={1}
              value={form.supervisor_response_days}
              onChange={(e) => set('supervisor_response_days', Number(e.target.value))}
              hint="Submitted work waiting longer than this is flagged on the dashboard."
            />

            <Input
              label="Student inactivity (days)"
              type="number"
              min={1}
              value={form.student_inactivity_days}
              onChange={(e) => set('student_inactivity_days', Number(e.target.value))}
              hint="A student with no progress for this long is flagged as gone quiet."
            />

            <Input
              label="Duplicate topic threshold (%)"
              type="number"
              min={0}
              max={100}
              value={form.similarity_threshold}
              onChange={(e) => set('similarity_threshold', Number(e.target.value))}
              hint="Topics scoring above this against past work are flagged as possible duplicates."
            />

            <Select
              label="Deadlines"
              value={form.use_fixed_stage_deadlines ? 'fixed' : 'per_supervisor'}
              onChange={(e) => set('use_fixed_stage_deadlines', e.target.value === 'fixed')}
            >
              <option value="fixed">One shared calendar for the department</option>
              <option value="per_supervisor">Each supervisor sets their own dates</option>
            </Select>
          </CardBody>
        </Card>
      </div>
    </>
  )
}
