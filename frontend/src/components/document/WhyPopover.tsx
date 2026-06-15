import * as Popover from '@radix-ui/react-popover'
import { Mic } from 'lucide-react'
import type { ReactNode } from 'react'

// Strip the machine prefix the pipeline prepends so the popover shows a clean reason.
const PREFIX = /^★\s*Spoken-only \(not on the slides\)\s*—\s*/

export function WhyPopover({ trigger, reason }: { trigger: ReactNode; reason: string }) {
  const clean = (reason ?? '').replace(PREFIX, '').trim()
  return (
    <Popover.Root>
      <Popover.Trigger asChild>{trigger}</Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          sideOffset={6}
          collisionPadding={12}
          className="z-50 max-w-xs rounded-xl border border-slate-200 bg-white p-3 font-sans text-sm shadow-lg dark:border-slate-700 dark:bg-slate-900"
        >
          <div className="mb-1 flex items-center gap-1.5 font-semibold text-spoken dark:text-amber-300">
            <Mic className="h-3.5 w-3.5" />
            Said in the lecture — not on the slides
          </div>
          <p className="text-slate-600 dark:text-slate-300">
            {clean || 'Captured from the audio and matched to this topic.'}
          </p>
          <Popover.Arrow className="fill-white dark:fill-slate-900" />
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  )
}
