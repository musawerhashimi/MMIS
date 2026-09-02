import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { STAGE_COLOR } from '@/lib/utils'
import type { StageCount } from '@/types'

/**
 * The same stage figures as a horizontal bar chart.
 *
 * Better than the donut when comparing two similar counts, and it reads
 * correctly on a narrow phone where a ring's labels would collide.
 */
export function StageBars({ data, height = 320 }: { data: StageCount[]; height?: number }) {
  const rows = data.filter((entry) => entry.count > 0)

  if (!rows.length) {
    return (
      <div className="flex items-center justify-center text-xs text-muted" style={{ height }}>
        No monographs yet.
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={rows} layout="vertical" margin={{ left: 8, right: 16, top: 4, bottom: 4 }}>
        <XAxis type="number" hide />
        <YAxis
          type="category"
          dataKey="label"
          width={132}
          tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          cursor={{ fill: 'var(--surface-sunken)' }}
          contentStyle={{
            background: 'var(--surface-raised)',
            border: '1px solid var(--border)',
            borderRadius: '0.5rem',
            fontSize: '12px',
            color: 'var(--text)',
          }}
        />
        <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={16}>
          {rows.map((entry) => (
            <Cell key={entry.stage} fill={STAGE_COLOR[entry.stage]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
