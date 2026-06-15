import { Link } from 'react-router-dom'
import type { SearchResult, SourceType } from '@/types/api'
import { cn } from '@/lib/cn'

const CHIP: Record<SourceType, string> = {
  slides: 'bg-blue-100 text-slides dark:bg-blue-500/15 dark:text-blue-300',
  spoken: 'bg-amber-100 text-spoken dark:bg-amber-500/15 dark:text-amber-300',
  diagram: 'bg-violet-100 text-diagram dark:bg-violet-500/15 dark:text-violet-300',
}
const LABEL: Record<SourceType, string> = {
  slides: 'Slides',
  spoken: 'Spoken',
  diagram: 'Diagram',
}

export function SearchResults({ results }: { results: SearchResult[] }) {
  if (results.length === 0) {
    return (
      <p className="py-10 text-center text-sm text-slate-500 dark:text-slate-400">
        No matches in this course.
      </p>
    )
  }
  return (
    <ul className="space-y-2">
      {results.map((r, i) => (
        <li key={i}>
          <Link
            to={`/lectures/${r.lecture_id}`}
            className="block rounded-xl border border-slate-200 bg-white p-4 transition-colors hover:border-brand-300 dark:border-slate-800 dark:bg-slate-900 dark:hover:border-brand-700"
          >
            <div className="mb-1 flex flex-wrap items-center gap-2">
              <span className={cn('rounded-full px-2 py-0.5 text-xs font-semibold', CHIP[r.source_type])}>
                {LABEL[r.source_type]}
              </span>
              <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
                {r.lecture_title} · {r.topic}
              </span>
            </div>
            <p className="line-clamp-2 text-sm text-slate-700 dark:text-slate-300">{r.text}</p>
          </Link>
        </li>
      ))}
    </ul>
  )
}
