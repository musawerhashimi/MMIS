import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { KeyRound, Search, UserPlus, Users } from 'lucide-react'
import { toast } from 'sonner'
import { api, errorMessage, fieldErrors } from '@/lib/api'
import { useAuth } from '@/stores/auth'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card, CardBody } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { Input, Select } from '@/components/ui/Input'
import { Badge } from '@/components/ui/Badge'
import { EmptyState } from '@/components/ui/EmptyState'
import { TableSkeleton } from '@/components/ui/Skeleton'
import { cn, initials } from '@/lib/utils'
import type { Paginated, User } from '@/types'

const ROLE_STYLE: Record<string, string> = {
  student: 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300',
  supervisor: 'bg-violet-100 text-violet-800 dark:bg-violet-950 dark:text-violet-300',
  hod: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300',
  committee: 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300',
  admin: 'bg-slate-200 text-slate-800 dark:bg-slate-800 dark:text-slate-200',
}

const ROLE_LABEL: Record<string, string> = {
  student: 'Student',
  supervisor: 'Supervisor',
  hod: 'Head of Department',
  committee: 'Committee Member',
  admin: 'Administrator',
}

export function PeoplePage() {
  const me = useAuth((s) => s.user)
  const [search, setSearch] = useState('')
  const [role, setRole] = useState('')
  const [createOpen, setCreateOpen] = useState(false)
  const [resetFor, setResetFor] = useState<User | null>(null)
  const queryClient = useQueryClient()

  const params = new URLSearchParams()
  if (search) params.set('search', search)
  if (role) params.set('role', role)

  const { data, isLoading } = useQuery({
    queryKey: ['users', params.toString()],
    queryFn: async () => {
      const { data } = await api.get<Paginated<User>>(`/auth/users/?${params.toString()}`)
      return data
    },
  })

  const toggleActive = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) =>
      api.post(`/auth/users/${id}/${active ? 'deactivate' : 'activate'}/`),
    onSuccess: (response) => {
      toast.success(response.data.detail)
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  return (
    <>
      <PageHeader
        title="People"
        description="Accounts for students, supervisors and staff."
        action={
          me?.permissions.is_admin ? (
            <Button icon={<UserPlus className="h-4 w-4" />} onClick={() => setCreateOpen(true)}>
              Add a person
            </Button>
          ) : undefined
        }
      />

      <Card className="mb-4 p-3">
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-[200px] flex-1">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-subtle" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by name or university ID"
                className="h-9.5 w-full rounded-lg border bg-[var(--surface)] pl-9 pr-3 text-sm outline-none focus:border-brand-500"
              />
            </div>
          </div>
          <div className="w-48">
            <Select value={role} onChange={(e) => setRole(e.target.value)} aria-label="Filter by role">
              <option value="">All roles</option>
              {Object.entries(ROLE_LABEL).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </Select>
          </div>
        </div>
      </Card>

      {isLoading ? (
        <TableSkeleton rows={6} />
      ) : !data?.results.length ? (
        <Card>
          <EmptyState icon={<Users className="h-5 w-5" />} title="Nobody matches that" />
        </Card>
      ) : (
        <Card>
          <CardBody className="p-0">
            <div className="divide-y">
              {data.results.map((person) => (
                <div key={person.id} className="flex items-center gap-3 px-5 py-3">
                  <span
                    className={cn(
                      'flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold',
                      person.is_active
                        ? 'bg-brand-600 text-white'
                        : 'surface-sunken text-subtle',
                    )}
                  >
                    {initials(person.full_name)}
                  </span>

                  <div className="min-w-0 flex-1">
                    <p className={cn('truncate text-sm font-medium', !person.is_active && 'text-subtle')}>
                      {person.display_name}
                      {!person.is_active && <span className="ml-2 text-[11px]">(inactive)</span>}
                    </p>
                    <p className="mt-0.5 truncate text-[11px] text-muted">
                      {person.username}
                      {person.student_profile && ` · ${person.student_profile.student_id}`}
                      {person.supervisor_profile?.specialization &&
                        ` · ${person.supervisor_profile.specialization}`}
                    </p>
                  </div>

                  {person.supervisor_profile && (
                    <span className="hidden shrink-0 text-[11px] text-muted sm:block">
                      {person.supervisor_profile.active_student_count}/
                      {person.supervisor_profile.effective_max_students} students
                    </span>
                  )}

                  <Badge className={ROLE_STYLE[person.role] ?? ''} size="sm">
                    {ROLE_LABEL[person.role] ?? person.role}
                  </Badge>

                  {me?.permissions.is_admin && person.id !== me.id && (
                    <div className="flex shrink-0 gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label="Reset password"
                        onClick={() => setResetFor(person)}
                      >
                        <KeyRound className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() =>
                          toggleActive.mutate({ id: person.id, active: person.is_active })
                        }
                      >
                        {person.is_active ? 'Deactivate' : 'Activate'}
                      </Button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardBody>
        </Card>
      )}

      <CreatePersonDialog open={createOpen} onClose={() => setCreateOpen(false)} />
      <ResetPasswordDialog person={resetFor} onClose={() => setResetFor(null)} />
    </>
  )
}

interface DepartmentOption {
  id: string
  name: string
  code: string
}

function CreatePersonDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const me = useAuth((s) => s.user)
  const [form, setForm] = useState({
    username: '',
    full_name: '',
    title: '',
    email: '',
    phone: '',
    role: 'student',
    password: '',
    student_id: '',
    department: me?.department ?? '',
  })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const queryClient = useQueryClient()

  // Asked for rather than copied from whoever is signed in: an administrator
  // who belongs to no department would otherwise create accounts that belong
  // to none either, and those accounts cannot do anything.
  const { data: departments } = useQuery({
    queryKey: ['departments', 'options'],
    queryFn: async () => {
      const { data } = await api.get<{ results: DepartmentOption[] }>(
        '/organization/departments/',
      )
      return data.results
    },
    enabled: open,
  })

  const create = useMutation({
    mutationFn: () =>
      api.post('/auth/users/', {
        ...form,
        student_id: form.role === 'student' ? form.student_id : undefined,
      }),
    onSuccess: () => {
      toast.success('Account created')
      queryClient.invalidateQueries({ queryKey: ['users'] })
      setForm({
        username: '', full_name: '', title: '', email: '', phone: '',
        role: 'student', password: '', student_id: '',
        department: me?.department ?? '',
      })
      onClose()
    },
    onError: (error) => {
      setErrors(fieldErrors(error))
      toast.error(errorMessage(error))
    },
  })

  function set(key: keyof typeof form, value: string) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Add a person"
      description="They sign in with the university ID you set here."
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={() => {
              if (!form.department) {
                setErrors({ department: 'Choose a department for this person.' })
                return
              }
              create.mutate()
            }}
            loading={create.isPending}
          >
            Create account
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label="University ID"
            required
            value={form.username}
            onChange={(e) => set('username', e.target.value)}
            error={errors.username}
            hint="What they type to sign in."
          />
          <Select label="Role" required value={form.role} onChange={(e) => set('role', e.target.value)}>
            {Object.entries(ROLE_LABEL).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </Select>
        </div>

        <Select
          label="Department"
          required
          value={form.department}
          onChange={(e) => set('department', e.target.value)}
          error={errors.department}
          hint="Without one, this person cannot propose or supervise anything."
        >
          <option value="">Choose a department</option>
          {departments?.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </Select>

        <div className="grid gap-4 sm:grid-cols-3">
          <Input
            label="Title"
            value={form.title}
            onChange={(e) => set('title', e.target.value)}
            placeholder="Dr."
          />
          <Input
            label="Full name"
            required
            className="sm:col-span-2"
            value={form.full_name}
            onChange={(e) => set('full_name', e.target.value)}
            error={errors.full_name}
          />
        </div>

        {form.role === 'student' && (
          <Input
            label="Student ID"
            required
            value={form.student_id}
            onChange={(e) => set('student_id', e.target.value)}
            error={errors.student_id}
          />
        )}

        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label="Email (optional)"
            type="email"
            value={form.email}
            onChange={(e) => set('email', e.target.value)}
            error={errors.email}
            hint="Not needed to sign in."
          />
          <Input
            label="Phone (optional)"
            value={form.phone}
            onChange={(e) => set('phone', e.target.value)}
          />
        </div>

        <Input
          label="Password"
          type="password"
          required
          value={form.password}
          onChange={(e) => set('password', e.target.value)}
          error={errors.password}
          hint="Tell them this, and ask them to change it once they sign in."
        />
      </div>
    </Modal>
  )
}

function ResetPasswordDialog({ person, onClose }: { person: User | null; onClose: () => void }) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  const reset = useMutation({
    mutationFn: () =>
      api.post(`/auth/users/${person!.id}/reset_password/`, { new_password: password }),
    onSuccess: (response) => {
      toast.success(response.data.detail)
      setPassword('')
      onClose()
    },
    onError: (e) => setError(errorMessage(e)),
  })

  return (
    <Modal
      open={Boolean(person)}
      onClose={onClose}
      title="Reset a password"
      description={`Set a new password for ${person?.full_name ?? ''}. Tell it to them directly — the system does not send email.`}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={() => {
              setError('')
              if (password.length < 8) return setError('Use at least 8 characters.')
              reset.mutate()
            }}
            loading={reset.isPending}
          >
            Reset
          </Button>
        </>
      }
    >
      <Input
        label="New password"
        type="password"
        required
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        error={error}
      />
    </Modal>
  )
}
