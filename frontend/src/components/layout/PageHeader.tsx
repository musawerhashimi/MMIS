import type { ReactNode } from 'react'

interface Props {
  title: string
  description?: string
  action?: ReactNode
  breadcrumb?: ReactNode
}

export function PageHeader({ title, description, action, breadcrumb }: Props) {
  return (
    <div className="mb-6">
      {breadcrumb && <div className="mb-2 text-xs text-subtle">{breadcrumb}</div>}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
          {description && <p className="mt-1 text-sm text-muted">{description}</p>}
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </div>
    </div>
  )
}
