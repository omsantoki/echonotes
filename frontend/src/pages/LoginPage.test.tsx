import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { LoginPage } from '@/pages/LoginPage'
import { ApiRequestError } from '@/lib/http'

const h = vi.hoisted(() => ({
  navigate: vi.fn(),
  signIn: vi.fn(),
  loginMock: vi.fn(),
  googleMock: vi.fn(),
}))

vi.mock('react-router-dom', async (orig) => ({
  ...(await orig<typeof import('react-router-dom')>()),
  useNavigate: () => h.navigate,
}))
vi.mock('@/lib/api', () => ({ auth: { login: h.loginMock, google: h.googleMock }, api: {} }))
vi.mock('@/hooks/useAuth', () => ({ useAuth: () => ({ signIn: h.signIn }) }))

beforeEach(() => vi.clearAllMocks())

describe('LoginPage', () => {
  it('logs in with email + password, stores the session, and navigates to /app', async () => {
    h.loginMock.mockResolvedValue({
      session_token: 't',
      user: { id: '1', email: 'a@b.com', auth_provider: 'local', email_verified: true },
    })
    const u = userEvent.setup()
    render(<MemoryRouter><LoginPage /></MemoryRouter>)

    await u.type(screen.getByLabelText('Email'), 'a@b.com')
    await u.type(screen.getByLabelText('Password'), 'password123')
    await u.click(screen.getByRole('button', { name: /log in/i }))

    await waitFor(() => expect(h.loginMock).toHaveBeenCalledWith('a@b.com', 'password123'))
    expect(h.signIn).toHaveBeenCalledWith('t', expect.objectContaining({ email: 'a@b.com' }))
    expect(h.navigate).toHaveBeenCalledWith('/app', { replace: true })
  })

  it('surfaces a backend error message on bad credentials', async () => {
    h.loginMock.mockRejectedValue(
      new ApiRequestError('Invalid email or password.', 'invalid_credentials', 401),
    )
    const u = userEvent.setup()
    render(<MemoryRouter><LoginPage /></MemoryRouter>)

    await u.type(screen.getByLabelText('Email'), 'a@b.com')
    await u.type(screen.getByLabelText('Password'), 'wrong')
    await u.click(screen.getByRole('button', { name: /log in/i }))

    expect(await screen.findByText('Invalid email or password.')).toBeInTheDocument()
    expect(h.signIn).not.toHaveBeenCalled()
    expect(h.navigate).not.toHaveBeenCalled()
  })
})
