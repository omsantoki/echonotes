import { Link, NavLink } from 'react-router-dom'
import { Logo } from '@/components/ui/Logo'
import { ThemeToggle } from '@/components/shell/ThemeToggle'
import { cn } from '@/lib/cn'

export function TopNav() {
  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/70 bg-white/80 backdrop-blur dark:border-slate-800/70 dark:bg-slate-950/80">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link
          to="/"
          className="rounded-lg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600"
        >
          <Logo />
        </Link>
        <nav className="flex items-center gap-1 sm:gap-2">
          <NavLink
            to="/app"
            className={({ isActive }) =>
              cn(
                'rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'text-brand-700 dark:text-brand-300'
                  : 'text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white',
              )
            }
          >
            My courses
          </NavLink>
          <ThemeToggle />
        </nav>
      </div>
    </header>
  )
}
