import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from '@/context/AuthContext'
import { useAuth } from '@/hooks/useAuth'
import { setToken, getToken, clearToken } from '@/lib/session'

vi.mock('@/lib/api', () => ({ auth: { me: vi.fn() }, api: {} }))
import { auth } from '@/lib/api'

const TEST_USER = { id: '1', email: 'x@y.com', auth_provider: 'local' as const, email_verified: true }

function Probe() {
  const a = useAuth()
  return (
    <div>
      <span data-testid="status">
        {a.loading ? 'loading' : a.isAuthenticated ? `in:${a.user?.email}` : 'out'}
      </span>
      <button onClick={() => a.signIn('tok', TEST_USER)}>in</button>
      <button onClick={() => a.signOut()}>out</button>
    </div>
  )
}

function setup() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <AuthProvider>
        <Probe />
      </AuthProvider>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  clearToken()
  vi.clearAllMocks()
})

describe('AuthContext', () => {
  it('starts logged out when there is no token', async () => {
    setup()
    await waitFor(() => expect(screen.getByTestId('status').textContent).toBe('out'))
  })

  it('signIn stores the token and sets the user', async () => {
    const u = userEvent.setup()
    setup()
    await u.click(screen.getByText('in'))
    expect(getToken()).toBe('tok')
    expect(screen.getByTestId('status').textContent).toBe('in:x@y.com')
  })

  it('signOut clears the token and the user', async () => {
    const u = userEvent.setup()
    setup()
    await u.click(screen.getByText('in'))
    await u.click(screen.getByText('out'))
    expect(getToken()).toBeNull()
    expect(screen.getByTestId('status').textContent).toBe('out')
  })

  it('bootstraps the user from an existing token via /me', async () => {
    setToken('existing')
    ;(auth.me as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: '9',
      email: 'me@y.com',
      auth_provider: 'local',
      email_verified: true,
    })
    setup()
    await waitFor(() => expect(screen.getByTestId('status').textContent).toBe('in:me@y.com'))
    expect(auth.me).toHaveBeenCalledTimes(1)
  })
})
