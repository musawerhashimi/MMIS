import { Check, Circle, X } from 'lucide-react'
import { cn, STAGE_COLOR } from '@/lib/utils'
import type { MonographStage } from '@/types'

/** The ladder a monograph climbs, in order. Terminal states sit outside it. */
const LADDER: { stage: MonographStage; short: string }[] = [
  { stage: 'draft', short: 'Draft' },
  { stage: 'topic_submitted', short: 'Topic' },
  { stage: 'topic_approved', short: 'Approved' },
  { stage: 'proposal_submitted', short: 'Proposal' },
  { stage: 'under_review', short: 'Review' },
  { stage: 'revision_required', short: 'Revision' },
  { stage: 'proposal_approved', short: 'Accepted' },
  { stage: 'research_in_progress', short: 'Research' },
  { stage: 'final_submission', short: 'Final' },
  { stage: 'final_review', short: 'Checking' },
  { stage: 'defense_scheduled', short: 'Scheduled' },
  { stage: 'defended', short: 'Defended' },
  { stage: 'completed', short: 'Done' },
]

const TERMINAL: MonographStage[] = ['rejected', 'withdrawn']

/**
 * A horizontal track showing how far a monograph has come.
 *
 * This is the screen a student looks at first, so it answers one question
 * immediately: where am I, and what is next.
 */
export function StageTrack({
  current,
  compact = false,
}: {
  current: MonographStage
  compact?: boolean
}) {
  const ended = TERMINAL.includes(current)
  const index = LADDER.findIndex((step) => step.stage === current)

  if (ended) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 dark:border-red-900 dark:bg-red-950/40">
        <X className="h-4 w-4 text-red-600 dark:text-red-400" />
        <span className="text-xs font-medium text-red-700 dark:text-red-300">
          {current === 'rejected' ? 'This monograph was rejected.' : 'This monograph was withdrawn.'}
        </span>
      </div>
    )
  }

  return (
    <div className="w-full overflow-x-auto pb-1">
      <div className={cn('flex min-w-max items-start', compact ? 'gap-0.5' : 'gap-1')}>
        {LADDER.map((step, i) => {
          const done = i < index
          const active = i === index
          const color = STAGE_COLOR[step.stage]

          return (
            <div key={step.stage} className="flex items-start">
              <div className={cn('flex flex-col items-center', compact ? 'w-14' : 'w-[68px]')}>
                <div
                  className={cn(
                    'flex items-center justify-center rounded-full border-2 transition-all',
                    compact ? 'h-5 w-5' : 'h-7 w-7',
                    active && 'scale-110 shadow-sm',
                  )}
                  style={{
                    borderColor: done || active ? color : 'var(--border-strong)',
                    background: done ? color : active ? color : 'var(--surface-raised)',
                  }}
                >
                  {done ? (
                    <Check className={cn('text-white', compact ? 'h-3 w-3' : 'h-4 w-4')} />
                  ) : active ? (
                    <Circle className={cn('fill-white text-white', compact ? 'h-2 w-2' : 'h-2.5 w-2.5')} />
                  ) : null}
                </div>
                <span
                  className={cn(
                    'mt-1.5 text-center leading-tight',
                    compact ? 'text-[9px]' : 'text-[10px]',
                    active ? 'font-semibold' : 'text-subtle',
                  )}
                >
                  {step.short}
                </span>
              </div>

              {i < LADDER.length - 1 && (
                <div
                  className={cn('mt-3 h-0.5 rounded-full', compact ? 'w-2' : 'w-3')}
                  style={{ background: i < index ? STAGE_COLOR[step.stage] : 'var(--border)' }}
                />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
