import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Mic } from 'lucide-react'
import { useLecture } from '@/hooks/useLecture'
import { NoteDocument } from '@/components/document/NoteDocument'
import { TableOfContents } from '@/components/document/TableOfContents'
import { ExportMenu } from '@/components/document/ExportMenu'
import { ProcessingTracker } from '@/components/processing/ProcessingTracker'
import { DeleteLectureButton } from '@/components/lecture/DeleteLectureButton'
import { ErrorState } from '@/components/ui/ErrorState'
import { Spinner } from '@/components/ui/Spinner'
import { buttonClasses } from '@/components/ui/Button'
import type { LectureDocument } from '@/types/api'

function countSpokenOnly(doc: LectureDocument): number {
  let n = 0
  for (const t of doc.topics ?? []) {
    for (const s of t.segments ?? []) {
      if (s.spoken_only || (s.source_type === 'spoken' && (s.reason ?? '').includes('★ Spoken-only'))) {
        n++
      }
    }
  }
  return n
}

export function LectureReadingPage() {
  const { lectureId } = useParams()
  const { data, isLoading, isError, error } = useLecture(lectureId)

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <Link
        to="/app"
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white"
      >
        <ArrowLeft className="h-4 w-4" />
        My courses
      </Link>

      {isLoading && (
        <div className="flex justify-center py-24">
          <Spinner className="h-8 w-8 text-brand-600" />
        </div>
      )}

      {isError && (
        <ErrorState
          message={(error as Error)?.message}
          action={
            <Link to="/app" className={buttonClasses('secondary', 'sm')}>
              Back to courses
            </Link>
          }
        />
      )}

      {data && data.status === 'failed' && (
        <ErrorState
          title="We couldn't finish these notes"
          message={data.progress.replace(/^Failed:\s*/, '')}
          action={
            <div className="flex items-center gap-2">
              <Link to="/app" className={buttonClasses('secondary', 'sm')}>
                Back to courses
              </Link>
              <DeleteLectureButton lectureId={data.id} />
            </div>
          }
        />
      )}

      {data && (data.status === 'processing' || data.status === 'uploaded') && (
        <div className="py-12">
          <div className="mb-8 text-center">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
              Composing your notes…
            </h1>
            <p className="mt-2 text-slate-500 dark:text-slate-400">
              This usually takes a couple of minutes. You can keep this tab open.
            </p>
          </div>
          <ProcessingTracker progress={data.progress} />
          <p className="mx-auto mt-8 max-w-md text-center text-xs text-slate-400 dark:text-slate-500">
            🔒 Your audio is processed in a temporary workspace and deleted the moment it's
            transcribed — it is never stored.
          </p>
        </div>
      )}

      {data && data.status === 'ready' && (
        <ReadyView title={data.title} doc={data.document} lectureId={data.id} />
      )}
    </div>
  )
}

function ReadyView({
  title,
  doc,
  lectureId,
}: {
  title: string
  doc: LectureDocument
  lectureId: string
}) {
  const spoken = countSpokenOnly(doc)
  return (
    <div className="lg:grid lg:grid-cols-[1fr_220px] lg:gap-10">
      <div className="min-w-0">
        <header className="mb-8 border-b border-slate-200 pb-6 dark:border-slate-800">
          <h1 className="font-serif text-3xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-4xl">
            {title}
          </h1>
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
            {spoken > 0 ? (
              <p className="inline-flex items-center gap-1.5 text-sm text-spoken dark:text-amber-300">
                <Mic className="h-4 w-4" />
                {spoken} insight{spoken === 1 ? '' : 's'} captured from the lecture that weren't on
                the slides
              </p>
            ) : (
              <span />
            )}
            <div className="flex items-center gap-2">
              <ExportMenu lectureId={lectureId} />
              <DeleteLectureButton lectureId={lectureId} title={title} />
            </div>
          </div>
        </header>
        <div className="mx-auto max-w-reading">
          <NoteDocument document={doc} />
        </div>
      </div>
      <aside className="hidden lg:block">
        <TableOfContents document={doc} />
      </aside>
    </div>
  )
}
