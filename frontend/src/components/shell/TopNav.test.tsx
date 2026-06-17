import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { TopNav } from '@/components/shell/TopNav'

vi.mock('@/hooks/useAuth', () => ({ useAuth: vi.fn() }))
vi.mock('@/hooks/useTheme', () => ({ useTheme: () => ({ theme: 'light', toggle: vi.fn() }) }))
import { useAuth } from '@/hooks/useAuth'

const mockAuth = useAuth as ReturnType<typeof vi.fn>

function renderNav() {
  return render(
    <MemoryRouter>
      <TopNav />
    </MemoryRouter>,
  )
}

beforeEach(() => vi.clearAllMocks())

describe('TopNav', () => {
  it('shows Log in / Sign up when logged out', () => {
    mockAuth.mockReturnValue({ isAuthenticated: false, loading: false, user: null, signOut: vi.fn() })
    renderNav()
    expect(screen.getByText('Log in')).toBeInTheDocument()
    expect(screen.getByText('Sign up')).toBeInTheDocument()
    expect(screen.queryByText('My courses')).toBeNull()
  })

  it('shows the user email + Log out when logged in', () => {
    mockAuth.mockReturnValue({
      isAuthenticated: true,
      loading: false,
      user: { email: 'a@b.com' },
      signOut: vi.fn(),
    })
    renderNav()
    expect(screen.getByText('a@b.com')).toBeInTheDocument()
    expect(screen.getByText('Log out')).toBeInTheDocument()
    expect(screen.getByText('My courses')).toBeInTheDocument()
  })

  it('hides the auth control while loading (avoids a flash of the wrong state)', () => {
    mockAuth.mockReturnValue({ isAuthenticated: false, loading: true, user: null, signOut: vi.fn() })
    renderNav()
    expect(screen.queryByText('Log in')).toBeNull()
    expect(screen.queryByText('Log out')).toBeNull()
  })

  it('logout calls signOut and hard-resets to the landing page', async () => {
    const signOut = vi.fn()
    mockAuth.mockReturnValue({ isAuthenticated: true, loading: false, user: { email: 'a@b.com' }, signOut })
    // jsdom's location.assign isn't spy-able, so replace the whole location object for this test.
    const original = window.location
    const assign = vi.fn()
    Object.defineProperty(window, 'location', { configurable: true, value: { ...original, assign } })
    try {
      const u = userEvent.setup()
      renderNav()
      await u.click(screen.getByText('Log out'))
      expect(signOut).toHaveBeenCalledTimes(1)
      expect(assign).toHaveBeenCalledWith('/')
    } finally {
      Object.defineProperty(window, 'location', { configurable: true, value: original })
    }
  })
})
