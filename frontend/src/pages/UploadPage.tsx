import { Link, useParams } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { useCourse } from '@/hooks/useCourse'
import { UploadForm } from '@/components/upload/UploadForm'

export function UploadPage() {
  const { courseId } = useParams()
  const { data: course } = useCourse(courseId)
  if (!courseId) return null

  return (
    <div className="mx-auto max-w-xl px-4 py-10 sm:px-6">
      <Link
        to={`/courses/${courseId}`}
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white"
      >
        <ArrowLeft className="h-4 w-4" />
        {course?.name ?? 'Course'}
      </Link>
      <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">Add a lecture</h1>
      <p className="mb-8 mt-1 text-slate-500 dark:text-slate-400">
        Upload the recording and the slides. EchoNotes transcribes the audio, aligns it to the
        slides, and composes one merged study document.
      </p>
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <UploadForm courseId={courseId} />
      </div>
    </div>
  )
}
