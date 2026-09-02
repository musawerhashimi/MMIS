import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, FileCheck, Printer } from 'lucide-react'
import { toast } from 'sonner'
import { api, errorMessage, tokens } from '@/lib/api'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card, CardBody } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { CardSkeleton } from '@/components/ui/Skeleton'
import { cn } from '@/lib/utils'

interface FormOption {
  key: string
  label: string
  available: boolean
  url: string
}

/**
 * The official forms the archive still needs on paper.
 *
 * A form only becomes available once the information it carries actually
 * exists, so nobody prints a result sheet for a defense that has not happened.
 */
export function FormsPage() {
  const { id = '' } = useParams()

  const { data, isLoading } = useQuery({
    queryKey: ['forms', id],
    queryFn: async () => {
      const { data } = await api.get<FormOption[]>(`/reports/forms/?monograph=${id}`)
      return data
    },
  })

  async function print(form: FormOption) {
    try {
      const response = await fetch(form.url, {
        headers: { Authorization: `Bearer ${tokens.access}` },
      })
      if (!response.ok) {
        const body = await response.json().catch(() => null)
        throw new Error(body?.error?.message ?? 'This form cannot be produced yet.')
      }
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      window.open(url, '_blank')
      // Give the new tab time to load before releasing the object URL.
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
    } catch (error) {
      toast.error(errorMessage(error))
    }
  }

  return (
    <>
      <PageHeader
        breadcrumb={
          <Link to={`/monographs/${id}`} className="inline-flex items-center gap-1 hover:underline">
            <ArrowLeft className="h-3 w-3" /> Back to the monograph
          </Link>
        }
        title="Official forms"
        description="Printed with signature lines, ready for the department stamp."
      />

      {isLoading ? (
        <CardSkeleton rows={4} />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {data?.map((form) => (
            <Card key={form.key} className={cn(!form.available && 'opacity-60')}>
              <CardBody className="flex items-start gap-3">
                <div
                  className={cn(
                    'flex h-9 w-9 shrink-0 items-center justify-center rounded-lg',
                    form.available
                      ? 'bg-brand-50 text-brand-600 dark:bg-brand-950/60 dark:text-brand-400'
                      : 'surface-sunken text-subtle',
                  )}
                >
                  <FileCheck className="h-4.5 w-4.5" />
                </div>

                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium">{form.label}</p>
                  <p className="mt-0.5 text-[11px] text-muted">
                    {form.available
                      ? 'Ready to print.'
                      : 'Not yet — the information this form needs is still missing.'}
                  </p>
                  <Button
                    size="sm"
                    variant={form.available ? 'primary' : 'secondary'}
                    disabled={!form.available}
                    className="mt-3"
                    icon={<Printer className="h-3.5 w-3.5" />}
                    onClick={() => print(form)}
                  >
                    Print
                  </Button>
                </div>
              </CardBody>
            </Card>
          ))}
        </div>
      )}
    </>
  )
}
