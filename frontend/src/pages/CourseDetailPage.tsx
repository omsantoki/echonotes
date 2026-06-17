import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Plus, Trash2, Upload } from 'lucide-react'
import { useCourse } from '@/hooks/useCourse'
import { useDeleteCourse } from '@/hooks/useCourses'
import { useCourseSearch } from '@/hooks/useCourseSearch'
import { useDebounce } from '@/hooks/useDebounce'
import { LectureCard } from '@/components/cards/LectureCard'
import { SearchBar } from '@/components/search/SearchBar'
import { SearchResults } from '@/components/search/SearchResults'
import { EmptyState } from '@/components/ui/EmptyState'
import { ErrorState } from '@/components/ui/ErrorState'
import { Spinner } from '@/components/ui/Spinner'
import { Button, buttonClasses } from '@/components/ui/Button'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'

export function CourseDetailPage() {
  const { courseId } = useParams()
  const navigate = useNavigate()
  const { data: course, isLoading, isError, error } = useCourse(courseId)
  const delCourse = useDeleteCourse()
  const [confirmDel, setConfirmDel] = useState(false)
  const [q, setQ] = useState('')
  const debounced = useDebounce(q, 300)
  const search = useCourseSearch(courseId, debounced)
  const searching = debounced.trim().length > 1

  return (
    <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6">
      <Link
        to="/app"
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white"
      >
        <ArrowLeft className="h-4 w-4" />
        My courses
      </Link>

      {isLoading && (
        <div className="flex justify-center py-20">
          <Spinner className="h-8 w-8 text-brand-600" />
        </div>
      )}
      {isError && (
        <ErrorState
          message={(error as Error)?.message}
          action={
            <Link to="/app" className={buttonClasses('secondary', 'sm')}>
              Back to my courses
            </Link>
          }
        />
      )}

      {course && (
        <>
          <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-3xl">
                {course.name}
              </h1>
              <p className="mt-1 text-slate-500 dark:text-slate-400">
                {course.lectures.length} {course.lectures.length === 1 ? 'lecture' : 'lectures'}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="secondary" onClick={() => setConfirmDel(true)}>
                <Trash2 className="h-4 w-4" />
                Delete course
              </Button>
              <Link to={`/courses/${course.id}/upload`} className={buttonClasses('primary', 'md')}>
                <Plus className="h-4 w-4" />
                Add lecture
              </Link>
            </div>
          </div>

          <div className="mb-6">
            <SearchBar value={q} onChange={setQ} />
          </div>

          {searching ? (
            <div>
              {search.isLoading && (
                <div className="flex justify-center py-10">
                  <Spinner className="h-6 w-6 text-brand-600" />
                </div>
              )}
              {search.isError && <ErrorState message={(search.error as Error)?.message} />}
              {search.data && <SearchResults results={search.data.results} />}
            </div>
          ) : course.lectures.length === 0 ? (
            <EmptyState
              icon={<Upload className="h-10 w-10" />}
              title="No lectures yet"
              description="Add a lecture's audio and slides — EchoNotes will merge them into source-labeled notes."
              action={
                <Link to={`/courses/${course.id}/upload`} className={buttonClasses('primary', 'md')}>
                  <Plus className="h-4 w-4" />
                  Add lecture
                </Link>
              }
            />
          ) : (
            <div className="space-y-2">
              {course.lectures.map((l) => (
                <LectureCard key={l.id} lecture={l} />
              ))}
            </div>
          )}

          <ConfirmDialog
            open={confirmDel}
            title="Delete course?"
            message={`"${course.name}" and all of its lectures and notes will be permanently deleted. This can't be undone.`}
            confirmLabel="Delete course"
            loading={delCourse.isPending}
            error={delCourse.isError ? (delCourse.error as Error).message : undefined}
            onConfirm={() => delCourse.mutate(course.id, { onSuccess: () => navigate('/app') })}
            onClose={() => setConfirmDel(false)}
          />
        </>
      )}
    </div>
  )
}
