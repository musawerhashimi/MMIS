import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { STAGE_COLOR } from '@/lib/utils'
import type { StageCount } from '@/types'

interface Props {
  data: StageCount[]
  height?: number
}

/**
 * How the department's monographs are spread across the stages.
 *
 * Empty stages are dropped from the ring — a zero-width slice is invisible
 * anyway, and leaving them in makes the legend unreadable.
 */
export function StageDonut({ data, height = 260 }: Props) {
  const slices = data.filter((entry) => entry.count > 0)
  const total = slices.reduce((sum, entry) => sum + entry.count, 0)

  if (!total) {
    return (
      <div
        className="flex items-center justify-center text-xs text-muted"
        style={{ height }}
      >
        No monographs yet.
      </div>
    )
  }

  return (
    <div className="relative" style={{ height }}>
      <ResponsiveContainer width="100%" height={height}>
        <PieChart>
          <Pie
            data={slices}
            dataKey="count"
            nameKey="label"
            innerRadius="62%"
            outerRadius="88%"
            paddingAngle={2}
            stroke="none"
          >
            {slices.map((entry) => (
              <Cell key={entry.stage} fill={STAGE_COLOR[entry.stage]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              background: 'var(--surface-raised)',
              border: '1px solid var(--border)',
              borderRadius: '0.5rem',
              fontSize: '12px',
              color: 'var(--text)',
            }}
            formatter={(value, name) => {
              const count = Number(value) || 0
              return [`${count} (${Math.round((count / total) * 100)}%)`, String(name)]
            }}
          />
        </PieChart>
      </ResponsiveContainer>

      {/* The total sits in the hole of the donut, where the eye lands first. */}
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-semibold tabular-nums">{total}</span>
        <span className="text-[11px] text-muted">monographs</span>
      </div>
    </div>
  )
}
