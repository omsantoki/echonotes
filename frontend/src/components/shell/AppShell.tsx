import { Outlet } from 'react-router-dom'
import { TopNav } from '@/components/shell/TopNav'
import { Footer } from '@/components/shell/Footer'

export function AppShell() {
  return (
    <div className="flex min-h-screen flex-col">
      <TopNav />
      <main className="flex-1">
        <Outlet />
      </main>
      <Footer />
    </div>
  )
}
