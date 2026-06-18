import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { SignUpPage } from '@/pages/SignUpPage'

const h = vi.hoisted(() => ({
  navigate: vi.fn(),
  signIn: vi.fn(),
  signupMock: vi.fn(),
  verifyMock: vi.fn(),
  setPwMock: vi.fn(),
  googleMock: vi.fn(),
}))

vi.mock('react-router-dom', async (orig) => ({
  ...(await orig<typeof import('react-router-dom')>()),
  useNavigate: () => h.navigate,
}))
vi.mock('@/lib/api', () => ({
  auth: {
    signup: h.signupMock,
    verifyOtp: h.verifyMock,
    setPassword: h.setPwMock,
    google: h.googleMock,
  },
  api: {},
}))
vi.mock('@/hooks/useAuth', () => ({ useAuth: () => ({ signIn: h.signIn }) }))

beforeEach(() => vi.clearAllMocks())

describe('SignUpPage (3-step flow)', () => {
  it('walks email → OTP → password, then signs in and lands in the app', async () => {
    h.signupMock.mockResolvedValue({ ok: true, message: '…' })
    h.verifyMock.mockResolvedValue({ set_password_token: 'spt' })
    h.setPwMock.mockResolvedValue({
      session_token: 't',
      user: { id: '1', email: 'a@b.com', auth_provider: 'local', email_verified: true },
    })
    const u = userEvent.setup()
    render(<MemoryRouter><SignUpPage /></MemoryRouter>)

    // Step 1: email
    await u.type(screen.getByLabelText('Email'), 'a@b.com')
    await u.click(screen.getByRole('button', { name: /send verification code/i }))
    await waitFor(() => expect(h.signupMock).toHaveBeenCalledWith('a@b.com'))

    // Step 2: OTP
    const otp = await screen.findByLabelText('6-digit code')
    await u.type(otp, '123456')
    await u.click(screen.getByRole('button', { name: /verify code/i }))
    await waitFor(() => expect(h.verifyMock).toHaveBeenCalledWith('a@b.com', '123456'))

    // Step 3: password
    const pw = await screen.findByLabelText('Password')
    await u.type(pw, 'password123')
    await u.type(screen.getByLabelText('Confirm password'), 'password123')
    await u.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() => expect(h.setPwMock).toHaveBeenCalledWith('spt', 'password123'))
    expect(h.signIn).toHaveBeenCalledWith('t', expect.objectContaining({ email: 'a@b.com' }))
    expect(h.navigate).toHaveBeenCalledWith('/app', { replace: true })
  })

  it('rejects mismatched passwords without calling the API', async () => {
    h.signupMock.mockResolvedValue({ ok: true, message: '…' })
    h.verifyMock.mockResolvedValue({ set_password_token: 'spt' })
    const u = userEvent.setup()
    render(<MemoryRouter><SignUpPage /></MemoryRouter>)

    await u.type(screen.getByLabelText('Email'), 'a@b.com')
    await u.click(screen.getByRole('button', { name: /send verification code/i }))
    await u.type(await screen.findByLabelText('6-digit code'), '123456')
    await u.click(screen.getByRole('button', { name: /verify code/i }))
    await u.type(await screen.findByLabelText('Password'), 'password123')
    await u.type(screen.getByLabelText('Confirm password'), 'different999')
    await u.click(screen.getByRole('button', { name: /create account/i }))

    expect(await screen.findByText('Passwords do not match.')).toBeInTheDocument()
    expect(h.setPwMock).not.toHaveBeenCalled()
  })
})
