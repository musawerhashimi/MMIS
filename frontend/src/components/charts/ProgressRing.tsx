import { CHART, cn } from '@/lib/utils'

interface Props {
  value: number
  size?: number
  thickness?: number
  color?: string
  label?: string
  sublabel?: string
  className?: string
}

/**
 * A circular progress indicator.
 *
 * Drawn as plain SVG rather than pulled from a chart library: it appears on
 * every monograph card, and a chart runtime per card would be a heavy price
 * on a slow phone.
 */
export function ProgressRing({
  value,
  size = 88,
  thickness = 8,
  color = CHART.brand,
  label,
  sublabel,
  className,
}: Props) {
  const clamped = Math.max(0, Math.min(100, value))
  const radius = (size - thickness) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (clamped / 100) * circumference

  return (
    <div className={cn('relative inline-flex items-center justify-center', className)}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--border)"
          strokeWidth={thickness}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={thickness}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 600ms cubic-bezier(0.16, 1, 0.3, 1)' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-lg font-semibold tabular-nums leading-none">
          {label ?? `${clamped}%`}
        </span>
        {sublabel && <span className="mt-0.5 text-[10px] text-muted">{sublabel}</span>}
      </div>
    </div>
  )
}
