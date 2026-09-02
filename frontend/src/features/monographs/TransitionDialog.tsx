import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { api, errorMessage } from '@/lib/api'
import { Modal } from '@/components/ui/Modal'
import { Button } from '@/components/ui/Button'
import { Textarea } from '@/components/ui/Input'
import type { AvailableAction } from '@/types'

interface Props {
  monographId: string
  action: AvailableAction | null
  onClose: () => void
}

/**
 * Confirming a stage change.
 *
 * Actions that require a written explanation say so and refuse to submit
 * without one, so a student never receives "revision required" with no
 * indication of what to change.
 */
export function TransitionDialog({ monographId, action, onClose }: Props) {
  const [note, setNote] = useState('')
  const [error, setError] = useState('')
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: async () => {
      const { data } = await api.post(`/monographs/${monographId}/transition/`, {
        target: action!.target,
        note,
      })
      return data
    },
    onSuccess: (data) => {
      toast.success(action!.label, {
        description: `Now at: ${data.monograph.stage_label}`,
      })
      queryClient.invalidateQueries({ queryKey: ['monograph', monographId] })
      queryClient.invalidateQueries({ queryKey: ['monographs'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      setNote('')
      onClose()
    },
    onError: (err) => setError(errorMessage(err)),
  })

  function submit() {
    setError('')
    if (action?.requires_note && !note.trim()) {
      setError('Please explain your decision — the student will see this.')
      return
    }
    mutation.mutate()
  }

  return (
    <Modal
      open={Boolean(action)}
      onClose={onClose}
      title={action?.label ?? ''}
      description={
        action?.requires_note
          ? 'Your explanation is recorded permanently and shown to the student.'
          : 'This will be recorded in the monograph history.'
      }
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={submit} loading={mutation.isPending}>
            Confirm
          </Button>
        </>
      }
    >
      <Textarea
        label={action?.requires_note ? 'Explanation' : 'Note (optional)'}
        required={action?.requires_note}
        value={note}
        onChange={(e) => setNote(e.target.value)}
        error={error}
        placeholder={
          action?.requires_note
            ? 'Say exactly what needs to change, so the student knows what to do next.'
            : 'Anything worth recording alongside this change.'
        }
        rows={5}
      />
    </Modal>
  )
}
