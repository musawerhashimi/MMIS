import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { CHART } from '@/lib/utils'
import type { Bottleneck } from '@/types'

/**
 * How long monographs sit at each stage.
 *
 * The longest bar is where the department actually loses time, which is
 * usually not where people assume it is.
 */
export function BottleneckChart({ data, height = 280 }: { data: Bottleneck[]; height?: number }) {
  const rows = data.filter((row) => row.average_days > 0).slice(0, 8)

  if (!rows.length) {
    return (
      <div className="flex items-center justify-center text-xs text-muted" style={{ height }}>
        Not enough history yet to show where time is spent.
      </div>
    )
  }

  const worst = Math.max(...rows.map((row) => row.average_days))

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={rows} layout="vertical" margin={{ left: 8, right: 28, top: 4, bottom: 4 }}>
        <XAxis type="number" hide />
        <YAxis
          type="category"
          dataKey="label"
          width={140}
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
          formatter={(value, _name, item) => {
            const row = item?.payload as Bottleneck | undefined
            const days = Number(value) || 0
            return [`${days} days average (${row?.sample_size ?? 0} moves)`, row?.label ?? '']
          }}
        />
        <Bar dataKey="average_days" radius={[0, 4, 4, 0]} barSize={16}>
          {rows.map((row) => (
            <Cell
              key={row.stage}
              fill={
                row.average_days === worst
                  ? CHART.warn
                  : CHART.brandSoft
              }
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
