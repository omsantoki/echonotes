import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { Spinner } from '@/components/ui/Spinner'

/**
 * Gate for the data pages (feature 002, Art. X). Unauthenticated users are sent to
 * /login with the intended destination preserved, so they land back where they meant
 * to go after signing in. The public landing page (/) is NOT wrapped in this guard.
 */
export function RequireAuth() {
  const { isAuthenticated, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="flex justify-center py-28">
        <Spinner className="h-8 w-8 text-brand-600" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  return <Outlet />
}
