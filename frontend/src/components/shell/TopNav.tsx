import { Link, NavLink } from 'react-router-dom'
import { LogOut } from 'lucide-react'
import { Logo } from '@/components/ui/Logo'
import { ThemeToggle } from '@/components/shell/ThemeToggle'
import { buttonClasses } from '@/components/ui/Button'
import { useAuth } from '@/hooks/useAuth'
import { cn } from '@/lib/cn'

export function TopNav() {
  const { isAuthenticated, loading, user, signOut } = useAuth()

  function logout() {
    signOut() // clears the token, user, and React Query cache
    // Hard reset to a clean, logged-out landing. This guarantees no per-account state
    // or "intended destination" (the route guard's `from`) survives into the next
    // login — otherwise logging out from a course page and signing in as a DIFFERENT
    // account would send you back to the previous account's course URL → 404.
    window.location.assign('/')
  }

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
          {isAuthenticated && (
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
          )}

          <ThemeToggle />

          {/* Auth control in the corner (feature 002, US-11). Hidden while the
              initial /me check is in flight to avoid a flash of the wrong state. */}
          {!loading &&
            (isAuthenticated ? (
              <div className="flex items-center gap-2 sm:gap-3">
                <span
                  className="hidden max-w-[12rem] truncate text-sm text-slate-500 dark:text-slate-400 sm:inline"
                  title={user?.email}
                >
                  {user?.email}
                </span>
                <button
                  onClick={logout}
                  className="inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white"
                >
                  <LogOut className="h-4 w-4" />
                  <span className="hidden sm:inline">Log out</span>
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-1 sm:gap-2">
                <Link
                  to="/login"
                  className="rounded-lg px-3 py-2 text-sm font-medium text-slate-600 transition-colors hover:text-slate-900 dark:text-slate-300 dark:hover:text-white"
                >
                  Log in
                </Link>
                <Link to="/signup" className={buttonClasses('primary', 'sm')}>
                  Sign up
                </Link>
              </div>
            ))}
        </nav>
      </div>
    </header>
  )
}
