import { renderInline } from '@/lib/markdown'
import { WhyPopover } from './WhyPopover'

/**
 * The core provenance cue: content said in the lecture but absent from the
 * slides. Highlighted with an amber underline + ★; click reveals the "why".
 */
export function SpokenOnly({ text, reason }: { text: string; reason: string }) {
  return (
    <WhyPopover
      reason={reason}
      trigger={
        <mark
          role="button"
          tabIndex={0}
          aria-label="Said in the lecture, not on the slides. Activate for details."
          className="cursor-help rounded-[3px] bg-spoken-soft px-[0.18em] py-[0.04em] text-slate-900 shadow-[inset_0_-0.5em_0_var(--color-spoken-line)] outline-none focus-visible:ring-2 focus-visible:ring-spoken dark:bg-amber-400/20 dark:text-amber-50 dark:underline dark:decoration-amber-400/60 dark:decoration-2 dark:shadow-none"
        >
          {renderInline(text)}
          <span className="font-bold text-spoken dark:text-amber-300"> ★</span>
        </mark>
      }
    />
  )
}
