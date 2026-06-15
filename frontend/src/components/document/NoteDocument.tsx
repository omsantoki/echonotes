import type { LectureDocument } from '@/types/api'
import { SourceLegend } from './SourceLegend'
import { TopicSection } from './TopicSection'

export function NoteDocument({ document }: { document: LectureDocument }) {
  const topics = document.topics ?? []
  if (topics.length === 0) {
    return <p className="text-slate-500 dark:text-slate-400">No notes were produced for this lecture.</p>
  }
  return (
    <article className="font-serif">
      <SourceLegend />
      {topics.map((topic, i) => (
        <TopicSection key={i} topic={topic} />
      ))}
    </article>
  )
}
