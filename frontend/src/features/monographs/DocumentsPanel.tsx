import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Check, ChevronDown, ChevronRight, Download, FileText, Upload,
} from 'lucide-react'
import { toast } from 'sonner'
import { api, errorMessage, tokens } from '@/lib/api'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { Input, Select, Textarea } from '@/components/ui/Input'
import { EmptyState } from '@/components/ui/EmptyState'
import { Skeleton } from '@/components/ui/Skeleton'
import { cn, formatDateTime, timeAgo } from '@/lib/utils'
import type { DocumentType, MonographDocument, Paginated } from '@/types'

const TYPES: { value: DocumentType; label: string }[] = [
  { value: 'proposal', label: 'Proposal' },
  { value: 'chapter', label: 'Chapter' },
  { value: 'final_monograph', label: 'Final Monograph' },
  { value: 'presentation', label: 'Defense Presentation' },
  { value: 'supporting', label: 'Supporting Material' },
  { value: 'signed_form', label: 'Signed Official Form' },
]

interface Props {
  monographId: string
  canUpload: boolean
  canApprove: boolean
}

export function DocumentsPanel({ monographId, canUpload, canApprove }: Props) {
  const [uploadOpen, setUploadOpen] = useState(false)
  const [expanded, setExpanded] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['documents', monographId],
    queryFn: async () => {
      const { data } = await api.get<Paginated<MonographDocument>>(
        `/documents/?monograph=${monographId}`,
      )
      return data.results
    },
  })

  const approve = useMutation({
    mutationFn: (id: string) => api.post(`/documents/${id}/approve/`),
    onSuccess: () => {
      toast.success('Document approved')
      queryClient.invalidateQueries({ queryKey: ['documents', monographId] })
      queryClient.invalidateQueries({ queryKey: ['monograph', monographId] })
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  /**
   * Downloads go through an authenticated request rather than a plain link:
   * the file is served by a permission-checked view, so the browser needs to
   * send the token.
   */
  async function download(versionId: string, filename: string) {
    try {
      const response = await fetch(`/api/v1/documents/versions/${versionId}/download/`, {
        headers: { Authorization: `Bearer ${tokens.access}` },
      })
      if (!response.ok) throw new Error('You cannot open this file.')
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      link.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      toast.error(errorMessage(e))
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-2 p-5">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-16 w-full" />
        ))}
      </div>
    )
  }

  return (
    <>
      {canUpload && (
        <div className="flex justify-end border-b px-5 py-3">
          <Button size="sm" icon={<Upload className="h-3.5 w-3.5" />} onClick={() => setUploadOpen(true)}>
            Upload a file
          </Button>
        </div>
      )}

      {!data?.length ? (
        <EmptyState
          icon={<FileText className="h-5 w-5" />}
          title="No documents yet"
          description={
            canUpload
              ? 'Upload your proposal, chapters and final monograph here.'
              : 'Nothing has been submitted yet.'
          }
          action={
            canUpload ? (
              <Button size="sm" onClick={() => setUploadOpen(true)}>
                Upload a file
              </Button>
            ) : undefined
          }
        />
      ) : (
        <div className="divide-y">
          {data.map((doc) => {
            const open = expanded === doc.id
            const current = doc.current_version
            return (
              <div key={doc.id}>
                <div className="flex items-center gap-3 px-5 py-3.5">
                  <button
                    onClick={() => setExpanded(open ? null : doc.id)}
                    className="flex h-6 w-6 shrink-0 items-center justify-center rounded text-[var(--text-muted)] hover:bg-[var(--surface-sunken)]"
                    aria-label={open ? 'Hide versions' : 'Show versions'}
                  >
                    {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                  </button>

                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="truncate text-sm font-medium">{doc.title}</p>
                      {doc.is_approved && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-medium text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                          <Check className="h-2.5 w-2.5" /> Approved
                        </span>
                      )}
                    </div>
                    <p className="mt-0.5 text-[11px] text-muted">
                      {doc.document_type_label}
                      {current && ` · v${current.version_number} · ${current.size_display}`}
                      {doc.version_count > 1 && ` · ${doc.version_count} versions`}
                      {current && ` · ${timeAgo(current.created_at)}`}
                    </p>
                  </div>

                  <div className="flex shrink-0 items-center gap-1">
                    {canApprove && !doc.is_approved && (
                      <Button
                        variant="ghost"
                        size="sm"
                        loading={approve.isPending}
                        onClick={() => approve.mutate(doc.id)}
                      >
                        Approve
                      </Button>
                    )}
                    {current && (
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label={`Download ${doc.title}`}
                        onClick={() => download(current.id, current.original_filename)}
                      >
                        <Download className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </div>

                {open && (
                  <div className="surface-sunken px-5 py-3">
                    <p className="mb-2 text-[11px] font-medium uppercase tracking-wide text-subtle">
                      Version history
                    </p>
                    <div className="space-y-2">
                      {doc.versions?.length
                        ? doc.versions.map((v) => (
                            <VersionRow key={v.id} version={v} onDownload={download} />
                          ))
                        : current && <VersionRow version={current} onDownload={download} />}
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      <UploadDialog
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        monographId={monographId}
      />
    </>
  )
}

function VersionRow({
  version,
  onDownload,
}: {
  version: MonographDocument['versions'] extends (infer V)[] | undefined ? V : never
  onDownload: (id: string, filename: string) => void
}) {
  return (
    <div className="flex items-start gap-3 rounded-lg bg-[var(--surface-raised)] px-3 py-2">
      <span className="mt-0.5 rounded bg-[var(--surface-sunken)] px-1.5 py-0.5 text-[10px] font-semibold tabular-nums">
        v{version.version_number}
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-[11px] font-medium">{version.original_filename}</p>
        <p className="text-[10px] text-subtle">
          {version.size_display} · {version.uploaded_by?.full_name ?? 'Unknown'} ·{' '}
          {formatDateTime(version.created_at)}
        </p>
        {version.change_note && (
          <p className="mt-1 text-[11px] italic text-muted">“{version.change_note}”</p>
        )}
      </div>
      <button
        onClick={() => onDownload(version.id, version.original_filename)}
        className="shrink-0 rounded p-1 text-[var(--text-muted)] hover:bg-[var(--surface-sunken)]"
        aria-label={`Download version ${version.version_number}`}
      >
        <Download className="h-3.5 w-3.5" />
      </button>
    </div>
  )
}

function UploadDialog({
  open,
  onClose,
  monographId,
}: {
  open: boolean
  onClose: () => void
  monographId: string
}) {
  const [type, setType] = useState<DocumentType>('proposal')
  const [chapter, setChapter] = useState('')
  const [note, setNote] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState('')
  const fileInput = useRef<HTMLInputElement>(null)
  const queryClient = useQueryClient()

  const upload = useMutation({
    mutationFn: async () => {
      const form = new FormData()
      form.append('file', file!)
      form.append('monograph', monographId)
      form.append('document_type', type)
      if (type === 'chapter' && chapter) form.append('chapter_number', chapter)
      if (note) form.append('change_note', note)

      const { data } = await api.post('/documents/upload/', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return data
    },
    onSuccess: (data) => {
      toast.success('File uploaded', {
        description: `${data.document.title} version ${data.version.version_number}`,
      })
      queryClient.invalidateQueries({ queryKey: ['documents', monographId] })
      queryClient.invalidateQueries({ queryKey: ['monograph', monographId] })
      reset()
      onClose()
    },
    onError: (e) => setError(errorMessage(e)),
  })

  function reset() {
    setFile(null)
    setNote('')
    setChapter('')
    setError('')
    if (fileInput.current) fileInput.current.value = ''
  }

  function submit() {
    setError('')
    if (!file) return setError('Choose a file to upload.')
    if (type === 'chapter' && !chapter) return setError('Which chapter is this?')
    upload.mutate()
  }

  return (
    <Modal
      open={open}
      onClose={() => {
        reset()
        onClose()
      }}
      title="Upload a file"
      description="Uploading again creates a new version. Nothing is ever overwritten."
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={submit} loading={upload.isPending}>
            Upload
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Select
          label="What is this file?"
          value={type}
          onChange={(e) => setType(e.target.value as DocumentType)}
          required
        >
          {TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </Select>

        {type === 'chapter' && (
          <Input
            label="Chapter number"
            type="number"
            min={1}
            value={chapter}
            onChange={(e) => setChapter(e.target.value)}
            required
          />
        )}

        <div>
          <label className="mb-1.5 block text-xs font-medium">
            File <span className="text-red-500">*</span>
          </label>
          <label
            className={cn(
              'flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-4 py-6 text-center transition-colors',
              file ? 'border-brand-400 bg-brand-50/50 dark:bg-brand-950/20' : 'hover:bg-[var(--surface-sunken)]',
            )}
          >
            <input
              ref={fileInput}
              type="file"
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.zip,.rar,.png,.jpg,.jpeg"
            />
            <Upload className="mb-2 h-5 w-5 text-subtle" />
            {file ? (
              <>
                <span className="text-xs font-medium">{file.name}</span>
                <span className="mt-0.5 text-[11px] text-subtle">
                  {(file.size / 1024 / 1024).toFixed(1)} MB
                </span>
              </>
            ) : (
              <>
                <span className="text-xs font-medium">Choose a file</span>
                <span className="mt-0.5 text-[11px] text-subtle">
                  PDF, Word, PowerPoint or an archive, up to 50 MB
                </span>
              </>
            )}
          </label>
        </div>

        <Textarea
          label="What changed? (optional)"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          rows={3}
          hint="Helps your supervisor see what you fixed since last time."
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
