import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronRight, FileText, Trash2 } from 'lucide-react'
import type { LectureSummary } from '@/types/api'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { useDeleteLecture } from '@/hooks/useLecture'
import { formatDate } from '@/lib/format'

export function LectureCard({ lecture }: { lecture: LectureSummary }) {
  const date = formatDate(lecture.date)
  const [confirm, setConfirm] = useState(false)
  const del = useDeleteLecture()

  return (
    <div className="group relative flex items-center justify-between gap-4 rounded-xl border border-slate-200 bg-white p-4 transition-colors hover:border-brand-300 hover:bg-brand-50/30 dark:border-slate-800 dark:bg-slate-900 dark:hover:border-brand-700 dark:hover:bg-slate-800/50">
      <Link
        to={`/lectures/${lecture.id}`}
        aria-label={`Open ${lecture.title}`}
        className="absolute inset-0 rounded-xl focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600"
      />
      <div className="flex min-w-0 items-center gap-3">
        <FileText className="h-5 w-5 shrink-0 text-slate-400" />
        <div className="min-w-0">
          <h3 className="truncate font-medium text-slate-900 dark:text-white">{lecture.title}</h3>
          {date && <p className="text-xs text-slate-500 dark:text-slate-400">{date}</p>}
        </div>
      </div>
      <div className="relative z-10 flex shrink-0 items-center gap-2">
        <StatusBadge status={lecture.status} />
        <button
          onClick={() => setConfirm(true)}
          aria-label={`Delete ${lecture.title}`}
          title="Delete lecture"
          className="rounded-lg p-2 text-slate-300 transition-colors hover:bg-red-50 hover:text-red-600 dark:text-slate-600 dark:hover:bg-red-500/10 dark:hover:text-red-400"
        >
          <Trash2 className="h-4 w-4" />
        </button>
        <ChevronRight className="h-5 w-5 text-slate-300 transition-colors group-hover:text-brand-500 dark:text-slate-600" />
      </div>

      <ConfirmDialog
        open={confirm}
        title="Delete lecture?"
        message={`"${lecture.title}" and its notes will be permanently deleted. This can't be undone.`}
        confirmLabel="Delete lecture"
        loading={del.isPending}
        error={del.isError ? (del.error as Error).message : undefined}
        onConfirm={() => del.mutate(lecture.id, { onSuccess: () => setConfirm(false) })}
        onClose={() => setConfirm(false)}
      />
    </div>
  )
}
