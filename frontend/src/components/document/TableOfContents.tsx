import type { LectureDocument } from '@/types/api'
import { slugify } from '@/lib/slug'

export function TableOfContents({ document }: { document: LectureDocument }) {
  const topics = document.topics ?? []
  if (topics.length < 2) return null
  return (
    <nav
      aria-label="Topics on this page"
      className="sticky top-24 hidden max-h-[calc(100vh-8rem)] overflow-auto lg:block"
    >
      <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">
        On this page
      </p>
      <ul className="space-y-1 border-l border-slate-200 dark:border-slate-800">
        {topics.map((t, i) => (
          <li key={i}>
            <a
              href={`#${slugify(t.topic)}`}
              className="-ml-px block border-l-2 border-transparent py-1 pl-3 text-sm text-slate-500 transition-colors hover:border-brand-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
            >
              {t.topic}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  )
}
