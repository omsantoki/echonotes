import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { RequireAuth } from '@/components/auth/RequireAuth'

vi.mock('@/hooks/useAuth', () => ({ useAuth: vi.fn() }))
import { useAuth } from '@/hooks/useAuth'

const mockAuth = useAuth as ReturnType<typeof vi.fn>

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route element={<RequireAuth />}>
          <Route path="/app" element={<div>PROTECTED</div>} />
        </Route>
        <Route path="/login" element={<div>LOGIN PAGE</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => vi.clearAllMocks())

describe('RequireAuth', () => {
  it('redirects unauthenticated users to /login', () => {
    mockAuth.mockReturnValue({ isAuthenticated: false, loading: false })
    renderAt('/app')
    expect(screen.getByText('LOGIN PAGE')).toBeInTheDocument()
    expect(screen.queryByText('PROTECTED')).toBeNull()
  })

  it('renders the protected page when authenticated', () => {
    mockAuth.mockReturnValue({ isAuthenticated: true, loading: false })
    renderAt('/app')
    expect(screen.getByText('PROTECTED')).toBeInTheDocument()
  })

  it('shows neither while the auth bootstrap is loading', () => {
    mockAuth.mockReturnValue({ isAuthenticated: false, loading: true })
    renderAt('/app')
    expect(screen.queryByText('LOGIN PAGE')).toBeNull()
    expect(screen.queryByText('PROTECTED')).toBeNull()
  })
})
