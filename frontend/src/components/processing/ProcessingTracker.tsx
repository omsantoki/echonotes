import { Check } from 'lucide-react'
import { Spinner } from '@/components/ui/Spinner'
import { cn } from '@/lib/cn'

// Stages mirror the progress strings written by app/pipeline.py.
const STAGES = [
  { label: 'Transcribing the audio', match: /transcrib/i },
  { label: 'Reading the slides', match: /slides/i },
  { label: 'Aligning speech to the slides', match: /align/i },
  { label: 'Describing diagrams', match: /diagram/i },
  { label: 'Composing your merged notes', match: /compos/i },
  { label: 'Saving to your course', match: /saving/i },
]

// The highest-indexed matching stage is the active one (later progress strings
// like "Aligning … to the slides" also contain earlier keywords).
function activeIndex(progress: string): number {
  if (/ready/i.test(progress)) return STAGES.length
  for (let i = STAGES.length - 1; i >= 0; i--) {
    if (STAGES[i].match.test(progress)) return i
  }
  return -1 // queued — nothing started yet
}

export function ProcessingTracker({ progress }: { progress: string }) {
  const active = activeIndex(progress)
  return (
    <div className="mx-auto max-w-md">
      <ol className="space-y-1">
        {STAGES.map((stage, i) => {
          const done = i < active
          const current = i === active
          return (
            <li
              key={i}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 transition-colors',
                current && 'bg-brand-50 dark:bg-brand-500/10',
              )}
            >
              <span
                className={cn(
                  'flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-sm font-medium',
                  done && 'bg-emerald-100 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-300',
                  current && 'bg-brand-600 text-white',
                  !done && !current && 'bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500',
                )}
              >
                {done ? <Check className="h-4 w-4" /> : current ? <Spinner className="h-4 w-4" /> : i + 1}
              </span>
              <span
                className={cn(
                  'text-sm font-medium',
                  done && 'text-slate-500 dark:text-slate-500',
                  current && 'text-slate-900 dark:text-white',
                  !done && !current && 'text-slate-400 dark:text-slate-600',
                )}
              >
                {stage.label}
              </span>
            </li>
          )
        })}
      </ol>
      <p className="mt-4 text-center text-sm text-slate-500 dark:text-slate-400" aria-live="polite">
        {progress}
      </p>
    </div>
  )
}
