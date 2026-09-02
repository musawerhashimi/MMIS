import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { api, errorMessage } from '@/lib/api'
import { useAuth } from '@/stores/auth'
import { Modal } from '@/components/ui/Modal'
import { Button } from '@/components/ui/Button'
import { Input, Select } from '@/components/ui/Input'
import type { MonographListItem, Paginated, SupervisorOption } from '@/types'

const ROLES = [
  { value: 'chair', label: 'Chair' },
  { value: 'supervisor', label: 'Supervisor' },
  { value: 'internal', label: 'Internal Examiner' },
  { value: 'external', label: 'External Examiner' },
  { value: 'secretary', label: 'Secretary' },
]

interface Seat {
  member_id: string
  role: string
}

/**
 * Setting a date and forming the committee.
 *
 * Both at once, because a defense with a date but no examiners is not
 * actually scheduled and the workflow will refuse to move on it.
 */
export function ScheduleDefenseDialog({
  open,
  onClose,
  monographId,
}: {
  open: boolean
  onClose: () => void
  monographId?: string
}) {
  const user = useAuth((s) => s.user)
  const [monograph, setMonograph] = useState(monographId ?? '')
  const [when, setWhen] = useState('')
  const [location, setLocation] = useState('')
  const [duration, setDuration] = useState('60')
  const [committee, setCommittee] = useState<Seat[]>([{ member_id: '', role: 'chair' }])
  const [error, setError] = useState('')
  const queryClient = useQueryClient()

  // Only monographs that have reached final review can be defended.
  const { data: ready } = useQuery({
    queryKey: ['monographs', 'ready-for-defense'],
    queryFn: async () => {
      const { data } = await api.get<Paginated<MonographListItem>>(
        '/monographs/?stage=final_review&stage=defense_scheduled',
      )
      return data.results
    },
    enabled: open && !monographId,
  })

  const { data: staff } = useQuery({
    queryKey: ['supervisors', user?.department],
    queryFn: async () => {
      const { data } = await api.get<SupervisorOption[]>('/auth/users/supervisors/')
      return data
    },
    enabled: open,
  })

  const schedule = useMutation({
    mutationFn: async () => {
      const { data } = await api.post('/defenses/schedule/', {
        monograph,
        scheduled_at: new Date(when).toISOString(),
        location,
        duration_minutes: Number(duration),
        committee: committee.filter((c) => c.member_id),
      })
      return data
    },
    onSuccess: () => {
      toast.success('Defense scheduled', {
        description: 'Everyone involved has been notified.',
      })
      queryClient.invalidateQueries({ queryKey: ['defenses'] })
      queryClient.invalidateQueries({ queryKey: ['monograph'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      reset()
      onClose()
    },
    onError: (e) => setError(errorMessage(e)),
  })

  function reset() {
    setWhen('')
    setLocation('')
    setDuration('60')
    setCommittee([{ member_id: '', role: 'chair' }])
    setError('')
  }

  function submit() {
    setError('')
    if (!monograph) return setError('Choose which monograph is being defended.')
    if (!when) return setError('Set a date and time.')
    const filled = committee.filter((c) => c.member_id)
    if (!filled.length) return setError('A defense needs a committee.')
    const ids = filled.map((c) => c.member_id)
    if (new Set(ids).size !== ids.length) {
      return setError('The same person cannot sit on the committee twice.')
    }
    schedule.mutate()
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Schedule a defense"
      description="The committee is notified as soon as you save this."
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={submit} loading={schedule.isPending}>
            Schedule
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        {!monographId && (
          <Select
            label="Monograph"
            required
            value={monograph}
            onChange={(e) => setMonograph(e.target.value)}
            hint="Only monographs that have passed final review appear here."
          >
            <option value="">Choose a monograph</option>
            {ready?.map((m) => (
              <option key={m.id} value={m.id}>
                {m.title} — {m.student_names.join(', ')}
              </option>
            ))}
          </Select>
        )}

        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label="Date and time"
            type="datetime-local"
            required
            value={when}
            onChange={(e) => setWhen(e.target.value)}
          />
          <Input
            label="Duration (minutes)"
            type="number"
            min={15}
            step={15}
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
          />
        </div>

        <Input
          label="Location"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          placeholder="e.g. Room 204, Main Building"
        />

        <div>
          <div className="mb-2 flex items-center justify-between">
            <label className="text-xs font-medium">
              Committee <span className="text-red-500">*</span>
            </label>
            <Button
              variant="ghost"
              size="sm"
              icon={<Plus className="h-3 w-3" />}
              onClick={() => setCommittee([...committee, { member_id: '', role: 'internal' }])}
            >
              Add member
            </Button>
          </div>
          <p className="mb-2 text-[11px] text-subtle">
            Your department's policy sets the minimum size.
          </p>

          <div className="space-y-2">
            {committee.map((seat, index) => (
              <div key={index} className="flex gap-2">
                <select
                  value={seat.member_id}
                  onChange={(e) => {
                    const next = [...committee]
                    next[index].member_id = e.target.value
                    setCommittee(next)
                  }}
                  className="h-9 flex-1 rounded-lg border bg-[var(--surface)] px-2 text-xs outline-none focus:border-brand-500"
                >
                  <option value="">Choose a person</option>
                  {staff?.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.display_name}
                    </option>
                  ))}
                </select>
                <select
                  value={seat.role}
                  onChange={(e) => {
                    const next = [...committee]
                    next[index].role = e.target.value
                    setCommittee(next)
                  }}
                  className="h-9 w-40 rounded-lg border bg-[var(--surface)] px-2 text-xs outline-none focus:border-brand-500"
                >
                  {ROLES.map((r) => (
                    <option key={r.value} value={r.value}>
                      {r.label}
                    </option>
                  ))}
                </select>
                {committee.length > 1 && (
                  <button
                    onClick={() => setCommittee(committee.filter((_, i) => i !== index))}
                    className="rounded-lg px-2 text-[var(--text-muted)] hover:bg-[var(--surface-sunken)]"
                    aria-label="Remove member"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                )}
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
