import { Outlet } from 'react-router-dom'
import { AuthProvider } from '@/context/AuthContext'
import { TopNav } from '@/components/shell/TopNav'
import { Footer } from '@/components/shell/Footer'

export function AppShell() {
  // AuthProvider lives here (inside the router) so TopNav and every page can use
  // useAuth and useNavigate. The landing page stays public; RequireAuth gates the rest.
  return (
    <AuthProvider>
      <div className="flex min-h-screen flex-col">
        <TopNav />
        <main className="flex-1">
          <Outlet />
        </main>
        <Footer />
      </div>
    </AuthProvider>
  )
}
