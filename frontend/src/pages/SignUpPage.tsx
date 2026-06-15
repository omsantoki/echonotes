import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { CheckCircle2 } from 'lucide-react'
import { auth } from '@/lib/api'
import { useAuth } from '@/hooks/useAuth'
import { AuthCard, Field, FormError } from '@/components/auth/AuthCard'
import { GoogleButton } from '@/components/auth/GoogleButton'
import { Button } from '@/components/ui/Button'

type Step = 'email' | 'otp' | 'password'

export function SignUpPage() {
  const navigate = useNavigate()
  const { signIn } = useAuth()

  const [step, setStep] = useState<Step>('email')
  const [email, setEmail] = useState('')
  const [otp, setOtp] = useState('')
  const [setPasswordToken, setSetPasswordToken] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState<string>()
  const [busy, setBusy] = useState(false)

  function fail(err: unknown, fallback: string) {
    setError(err instanceof Error ? err.message : fallback)
  }

  async function submitEmail(e: FormEvent) {
    e.preventDefault()
    setError(undefined)
    setBusy(true)
    try {
      await auth.signup(email.trim())
      setStep('otp') // response is intentionally neutral; always advance to code entry
    } catch (err) {
      fail(err, 'Could not start sign-up.')
    } finally {
      setBusy(false)
    }
  }

  async function submitOtp(e: FormEvent) {
    e.preventDefault()
    setError(undefined)
    setBusy(true)
    try {
      const { set_password_token } = await auth.verifyOtp(email.trim(), otp.trim())
      setSetPasswordToken(set_password_token)
      setStep('password')
    } catch (err) {
      fail(err, 'That code is invalid or expired.')
    } finally {
      setBusy(false)
    }
  }

  async function submitPassword(e: FormEvent) {
    e.preventDefault()
    setError(undefined)
    if (password !== confirm) {
      setError('Passwords do not match.')
      return
    }
    setBusy(true)
    try {
      const { session_token, user } = await auth.setPassword(setPasswordToken, password)
      signIn(session_token, user)
      navigate('/app', { replace: true })
    } catch (err) {
      fail(err, 'Could not set your password.')
    } finally {
      setBusy(false)
    }
  }

  async function resendCode() {
    setError(undefined)
    try {
      await auth.signup(email.trim())
    } catch (err) {
      fail(err, 'Could not resend the code.')
    }
  }

  async function onGoogle(idToken: string) {
    setError(undefined)
    try {
      const { session_token, user } = await auth.google(idToken)
      signIn(session_token, user)
      navigate('/app', { replace: true })
    } catch (err) {
      fail(err, 'Google sign-in failed.')
    }
  }

  const footer = (
    <>
      Already have an account?{' '}
      <Link to="/login" className="font-medium text-brand-600 hover:underline dark:text-brand-400">
        Log in
      </Link>
    </>
  )

  if (step === 'email') {
    return (
      <AuthCard title="Create your account" subtitle="Start with your email — we'll send a code to verify it." footer={footer}>
        <form onSubmit={submitEmail} className="space-y-4">
          <Field
            label="Email"
            id="email"
            type="email"
            autoComplete="email"
            autoFocus
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <FormError message={error} />
          <Button type="submit" disabled={busy} className="w-full">
            {busy ? 'Sending code…' : 'Send verification code'}
          </Button>
        </form>
        <GoogleButton onCredential={onGoogle} onError={setError} />
      </AuthCard>
    )
  }

  if (step === 'otp') {
    return (
      <AuthCard
        title="Check your email"
        subtitle={
          <>
            We sent a 6-digit code to <span className="font-medium text-slate-700 dark:text-slate-200">{email}</span>.
            <br />
            <span className="text-xs">In local dev the code is printed to the server log.</span>
          </>
        }
        footer={footer}
      >
        <form onSubmit={submitOtp} className="space-y-4">
          <Field
            label="6-digit code"
            id="otp"
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={6}
            autoFocus
            required
            value={otp}
            onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
          />
          <FormError message={error} />
          <Button type="submit" disabled={busy} className="w-full">
            {busy ? 'Verifying…' : 'Verify code'}
          </Button>
          <button
            type="button"
            onClick={resendCode}
            className="w-full text-center text-xs font-medium text-brand-600 hover:underline dark:text-brand-400"
          >
            Resend code
          </button>
        </form>
      </AuthCard>
    )
  }

  return (
    <AuthCard
      title="Choose a password"
      subtitle={
        <span className="inline-flex items-center gap-1.5">
          <CheckCircle2 className="h-4 w-4 text-emerald-500" /> Email verified — set a password to finish.
        </span>
      }
      footer={footer}
    >
      <form onSubmit={submitPassword} className="space-y-4">
        <Field
          label="Password"
          id="password"
          type="password"
          autoComplete="new-password"
          minLength={8}
          autoFocus
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <Field
          label="Confirm password"
          id="confirm"
          type="password"
          autoComplete="new-password"
          minLength={8}
          required
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
        />
        <p className="text-xs text-slate-400 dark:text-slate-500">At least 8 characters.</p>
        <FormError message={error} />
        <Button type="submit" disabled={busy} className="w-full">
          {busy ? 'Creating account…' : 'Create account'}
        </Button>
      </form>
    </AuthCard>
  )
}
