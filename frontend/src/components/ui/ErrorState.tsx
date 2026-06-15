import type { ReactNode } from 'react'

export function ErrorState({
  title = 'Something went wrong',
  message,
  action,
}: {
  title?: string
  message?: string
  action?: ReactNode
}) {
  return (
    <div className="rounded-2xl border border-red-200 bg-red-50 px-6 py-8 text-center dark:border-red-500/30 dark:bg-red-500/10">
      <h3 className="text-base font-semibold text-red-800 dark:text-red-300">{title}</h3>
      {message && (
        <p className="mt-1 text-sm text-red-700/80 dark:text-red-300/80">{message}</p>
      )}
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  )
}
