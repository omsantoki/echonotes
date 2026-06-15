import { cn } from '@/lib/cn'

export function Logo({ className }: { className?: string }) {
  return (
    <span className={cn('inline-flex items-center gap-2', className)}>
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-white shadow-sm">
        <svg
          viewBox="0 0 32 32"
          className="h-5 w-5"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.6"
          strokeLinecap="round"
          aria-hidden="true"
        >
          <line x1="9" y1="13" x2="9" y2="19" />
          <line x1="15" y1="8" x2="15" y2="24" />
          <line x1="21" y1="11" x2="21" y2="21" />
          <line x1="26" y1="14.5" x2="26" y2="17.5" />
        </svg>
      </span>
      <span className="text-lg font-bold tracking-tight text-slate-900 dark:text-white">
        Echo<span className="text-brand-600 dark:text-brand-400">Notes</span>
      </span>
    </span>
  )
}
