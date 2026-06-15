import { useState } from 'react'
import { Link } from 'react-router-dom'
import { BookOpen, ChevronRight, Trash2 } from 'lucide-react'
import type { CourseSummary } from '@/types/api'
import { useDeleteCourse } from '@/hooks/useCourses'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'

export function CourseCard({ course }: { course: CourseSummary }) {
  const n = course.lecture_count
  const [confirm, setConfirm] = useState(false)
  const del = useDeleteCourse()

  return (
    <div className="group relative flex items-center justify-between rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:border-brand-300 hover:shadow-md dark:border-slate-800 dark:bg-slate-900 dark:hover:border-brand-700">
      {/* Stretched link: the whole card is clickable, but the delete button (z-10) isn't covered. */}
      <Link
        to={`/courses/${course.id}`}
        aria-label={`Open ${course.name}`}
        className="absolute inset-0 rounded-2xl focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600"
      />
      <div className="flex min-w-0 items-center gap-4">
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-300">
          <BookOpen className="h-5 w-5" />
        </span>
        <div className="min-w-0">
          <h3 className="truncate font-semibold text-slate-900 dark:text-white">{course.name}</h3>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {n} {n === 1 ? 'lecture' : 'lectures'}
          </p>
        </div>
      </div>
      <div className="relative z-10 flex items-center gap-1">
        <button
          onClick={() => setConfirm(true)}
          aria-label={`Delete ${course.name}`}
          title="Delete course"
          className="rounded-lg p-2 text-slate-300 transition-colors hover:bg-red-50 hover:text-red-600 dark:text-slate-600 dark:hover:bg-red-500/10 dark:hover:text-red-400"
        >
          <Trash2 className="h-4 w-4" />
        </button>
        <ChevronRight className="h-5 w-5 text-slate-300 transition-colors group-hover:text-brand-500 dark:text-slate-600" />
      </div>

      <ConfirmDialog
        open={confirm}
        title="Delete course?"
        message={`"${course.name}" and all of its lectures and notes will be permanently deleted. This can't be undone.`}
        confirmLabel="Delete course"
        loading={del.isPending}
        error={del.isError ? (del.error as Error).message : undefined}
        onConfirm={() => del.mutate(course.id, { onSuccess: () => setConfirm(false) })}
        onClose={() => setConfirm(false)}
      />
    </div>
  )
}
