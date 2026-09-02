import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { CHART } from '@/lib/utils'
import type { SupervisorLoad } from '@/types'

/**
 * How many students each supervisor carries.
 *
 * Anyone over their agreed limit is drawn in red, because spotting the
 * overloaded supervisor is the entire reason this chart exists.
 */
export function WorkloadChart({ data, height = 280 }: { data: SupervisorLoad[]; height?: number }) {
  const rows = data.filter((row) => row.active > 0 || row.completed > 0)

  if (!rows.length) {
    return (
      <div className="flex items-center justify-center text-xs text-muted" style={{ height }}>
        No supervision assigned yet.
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={rows} layout="vertical" margin={{ left: 8, right: 24, top: 4, bottom: 4 }}>
        <XAxis type="number" hide />
        <YAxis
          type="category"
          dataKey="name"
          width={150}
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
            const row = item?.payload as SupervisorLoad | undefined
            const cap = row?.capacity ? ` of ${row.capacity}` : ''
            return [`${Number(value) || 0}${cap} students`, 'Active']
          }}
        />
        <Bar dataKey="active" radius={[0, 4, 4, 0]} barSize={16}>
          {rows.map((row) => (
            <Cell
              key={row.id}
              fill={row.over_capacity ? CHART.danger : CHART.brand}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
