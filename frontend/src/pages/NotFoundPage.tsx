import { Link } from 'react-router-dom'
import { buttonClasses } from '@/components/ui/Button'

export function NotFoundPage() {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center px-4 py-28 text-center">
      <p className="text-5xl font-bold text-brand-600 dark:text-brand-400">404</p>
      <h1 className="mt-4 text-xl font-semibold text-slate-900 dark:text-white">Page not found</h1>
      <p className="mt-2 text-slate-500 dark:text-slate-400">
        The page you're looking for doesn't exist or may have moved.
      </p>
      <Link to="/app" className={buttonClasses('primary', 'md', 'mt-6')}>
        Go to my courses
      </Link>
    </div>
  )
}
