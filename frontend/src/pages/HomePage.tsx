import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { BookOpen, Plus } from 'lucide-react'
import { useCourses, useCreateCourse } from '@/hooks/useCourses'
import { CourseCard } from '@/components/cards/CourseCard'
import { Button } from '@/components/ui/Button'
import { Modal } from '@/components/ui/Modal'
import { EmptyState } from '@/components/ui/EmptyState'
import { ErrorState } from '@/components/ui/ErrorState'
import { Spinner } from '@/components/ui/Spinner'

export function HomePage() {
  const { data: courses, isLoading, isError, error, refetch } = useCourses()
  const [open, setOpen] = useState(false)

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-3xl">
            My courses
          </h1>
          <p className="mt-1 text-slate-500 dark:text-slate-400">
            Each course keeps its lectures together, so notes build on each other.
          </p>
        </div>
        <Button onClick={() => setOpen(true)}>
          <Plus className="h-4 w-4" />
          New course
        </Button>
      </div>

      {isLoading && (
        <div className="flex justify-center py-20">
          <Spinner className="h-8 w-8 text-brand-600" />
        </div>
      )}

      {isError && (
        <ErrorState
          message={(error as Error)?.message}
          action={
            <Button variant="secondary" size="sm" onClick={() => refetch()}>
              Retry
            </Button>
          }
        />
      )}

      {courses && courses.length === 0 && (
        <EmptyState
          icon={<BookOpen className="h-10 w-10" />}
          title="No courses yet"
          description="Create your first course, then add a lecture's audio and slides to generate merged notes."
          action={
            <Button onClick={() => setOpen(true)}>
              <Plus className="h-4 w-4" />
              New course
            </Button>
          }
        />
      )}

      {courses && courses.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {courses.map((c) => (
            <CourseCard key={c.id} course={c} />
          ))}
        </div>
      )}

      <CreateCourseModal open={open} onClose={() => setOpen(false)} />
    </div>
  )
}

function CreateCourseModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const navigate = useNavigate()
  const { mutate, isPending, error } = useCreateCourse()
  const [name, setName] = useState('')

  function submit(e: FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    mutate(name.trim(), {
      onSuccess: (course) => {
        setName('')
        onClose()
        navigate(`/courses/${course.id}`)
      },
    })
  }

  return (
    <Modal open={open} onClose={onClose} title="New course">
      <form onSubmit={submit} className="space-y-4">
        <div>
          <label
            htmlFor="course-name"
            className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300"
          >
            Course name
          </label>
          <input
            id="course-name"
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Biology 101"
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
          />
        </div>
        {error && <p className="text-sm text-red-600 dark:text-red-400">{(error as Error).message}</p>}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={isPending || !name.trim()}>
            {isPending ? 'Creating…' : 'Create course'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
