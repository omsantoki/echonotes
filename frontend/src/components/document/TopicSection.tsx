import type { Segment, Topic } from '@/types/api'
import { renderInline } from '@/lib/markdown'
import { slugify } from '@/lib/slug'
import { SpokenOnly } from './SpokenOnly'
import { DiagramFigure } from './DiagramFigure'
import { BuildsOnLink } from './BuildsOnLink'

function isSpokenOnly(seg: Segment): boolean {
  return (
    seg.spoken_only ||
    (seg.source_type === 'spoken' && (seg.reason ?? '').includes('★ Spoken-only'))
  )
}

function SegmentInline({ seg, stripBullet }: { seg: Segment; stripBullet?: boolean }) {
  let text = (seg.text ?? '').trim()
  if (stripBullet && text.startsWith('- ')) text = text.slice(2).trim()
  if (!isSpokenOnly(seg)) return <>{renderInline(text)}</>
  return <SpokenOnly text={text} reason={seg.reason} />
}

// Mirror app/render.py:_topic_html — coalesce prose into paragraphs, group "- "
// lines into a list, and flush both when a diagram interrupts the flow.
type Block =
  | { kind: 'para'; segs: Segment[] }
  | { kind: 'list'; items: Segment[] }
  | { kind: 'figure'; seg: Segment }

function toBlocks(segments: Segment[]): Block[] {
  const blocks: Block[] = []
  let para: Segment[] = []
  let bullets: Segment[] = []
  const flushPara = () => {
    if (para.length) {
      blocks.push({ kind: 'para', segs: para })
      para = []
    }
  }
  const flushBullets = () => {
    if (bullets.length) {
      blocks.push({ kind: 'list', items: bullets })
      bullets = []
    }
  }
  for (const seg of segments) {
    if (seg.source_type === 'diagram') {
      flushBullets()
      flushPara()
      blocks.push({ kind: 'figure', seg })
      continue
    }
    const text = (seg.text ?? '').trim()
    if (!text) continue
    if (text.startsWith('- ')) {
      flushPara()
      bullets.push(seg)
    } else {
      flushBullets()
      para.push(seg)
    }
  }
  flushBullets()
  flushPara()
  return blocks
}

export function TopicSection({ topic }: { topic: Topic }) {
  const blocks = toBlocks(topic.segments ?? [])
  return (
    <section id={slugify(topic.topic)} className="scroll-mt-24">
      <h2 className="mt-12 border-b border-slate-200 pb-2 font-serif text-2xl font-semibold text-slate-900 first:mt-0 dark:border-slate-800 dark:text-white">
        {topic.topic || 'Notes'}
      </h2>
      {topic.builds_on && (
        <div className="mt-3">
          <BuildsOnLink link={topic.builds_on} />
        </div>
      )}
      <div className="mt-4 space-y-4 text-[1.075rem] leading-relaxed text-slate-700 dark:text-slate-300">
        {blocks.length === 0 && <p className="text-slate-400">No content.</p>}
        {blocks.map((block, i) => {
          if (block.kind === 'figure') return <DiagramFigure key={i} seg={block.seg} />
          if (block.kind === 'list') {
            return (
              <ul key={i} className="list-disc space-y-1.5 pl-6 marker:text-slate-400">
                {block.items.map((seg, j) => (
                  <li key={j}>
                    <SegmentInline seg={seg} stripBullet />
                  </li>
                ))}
              </ul>
            )
          }
          return (
            <p key={i}>
              {block.segs.map((seg, j) => (
                <span key={j}>
                  <SegmentInline seg={seg} />{' '}
                </span>
              ))}
            </p>
          )
        })}
      </div>
    </section>
  )
}
