import { Link } from 'react-router-dom'
import { CornerDownRight } from 'lucide-react'
import type { BuildsOn } from '@/types/api'
import { percent } from '@/lib/format'

export function BuildsOnLink({ link }: { link: BuildsOn }) {
  const sim = percent(link.similarity)
  return (
    <p className="flex flex-wrap items-center gap-1 font-sans text-sm text-diagram dark:text-violet-300">
      <CornerDownRight className="h-4 w-4 shrink-0" />
      <span>Builds on</span>
      <Link
        to={`/lectures/${link.lecture_id}`}
        className="font-medium underline decoration-diagram/40 underline-offset-2 hover:decoration-diagram"
      >
        {link.lecture_title || 'an earlier lecture'}
      </Link>
      {link.topic && <span className="text-slate-500 dark:text-slate-400">— {link.topic}</span>}
      {sim && <span className="text-slate-400 dark:text-slate-500">· {sim} similar</span>}
    </p>
  )
}
