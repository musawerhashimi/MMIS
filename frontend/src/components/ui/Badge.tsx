import type { ReactNode } from 'react'
import { cn, STAGE_BADGE } from '@/lib/utils'
import type { MonographStage } from '@/types'

interface Props {
  children: ReactNode
  className?: string
  size?: 'sm' | 'md'
}

export function Badge({ children, className, size = 'md' }: Props) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full font-medium whitespace-nowrap',
        size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs',
        className,
      )}
    >
      {children}
    </span>
  )
}

/** A stage badge, coloured consistently with the charts and the timeline. */
export function StageBadge({
  stage,
  label,
  size = 'md',
}: {
  stage: MonographStage
  label: string
  size?: 'sm' | 'md'
}) {
  return (
    <Badge className={STAGE_BADGE[stage]} size={size}>
      {label}
    </Badge>
  )
}
