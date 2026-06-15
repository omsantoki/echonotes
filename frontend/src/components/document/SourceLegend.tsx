import { FileText, Image as ImageIcon } from 'lucide-react'

export function SourceLegend() {
  return (
    <div className="mb-8 flex flex-wrap items-center gap-x-5 gap-y-2 rounded-xl border border-slate-200 bg-white/60 px-4 py-3 font-sans text-sm text-slate-600 dark:border-slate-800 dark:bg-slate-900/50 dark:text-slate-300">
      <span className="flex items-center gap-1.5">
        <FileText className="h-4 w-4 text-slides" />
        Slides &amp; lecture, woven together
      </span>
      <span className="flex items-center gap-1.5">
        <mark className="rounded-[3px] bg-spoken-soft px-1 text-slate-900 dark:bg-amber-400/20 dark:text-amber-100">
          said only aloud ★
        </mark>
        <span className="text-slate-400 dark:text-slate-500">— click for “why”</span>
      </span>
      <span className="flex items-center gap-1.5">
        <ImageIcon className="h-4 w-4 text-diagram" />
        Diagrams preserved in place
      </span>
    </div>
  )
}
