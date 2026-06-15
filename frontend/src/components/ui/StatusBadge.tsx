import type { LectureStatus } from '@/types/api'
import { cn } from '@/lib/cn'

const STYLES: Record<LectureStatus, { label: string; cls: string }> = {
  uploaded: {
    label: 'Uploaded',
    cls: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
  },
  processing: {
    label: 'Processing',
    cls: 'bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-300',
  },
  ready: {
    label: 'Ready',
    cls: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-300',
  },
  failed: {
    label: 'Failed',
    cls: 'bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-300',
  },
}

export function StatusBadge({
  status,
  className,
}: {
  status: LectureStatus
  className?: string
}) {
  const s = STYLES[status] ?? STYLES.uploaded
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold',
        s.cls,
        className,
      )}
    >
      {status === 'processing' && (
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />
      )}
      {s.label}
    </span>
  )
}
