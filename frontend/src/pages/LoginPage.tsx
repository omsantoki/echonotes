import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { auth } from '@/lib/api'
import { useAuth } from '@/hooks/useAuth'
import { AuthCard, Field, FormError } from '@/components/auth/AuthCard'
import { GoogleButton } from '@/components/auth/GoogleButton'
import { Button } from '@/components/ui/Button'

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { signIn } = useAuth()
  const dest = (location.state as { from?: { pathname: string } } | null)?.from?.pathname ?? '/app'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string>()
  const [busy, setBusy] = useState(false)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setError(undefined)
    setBusy(true)
    try {
      const { session_token, user } = await auth.login(email.trim(), password)
      signIn(session_token, user)
      navigate(dest, { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not log in.')
    } finally {
      setBusy(false)
    }
  }

  async function onGoogle(idToken: string) {
    setError(undefined)
    try {
      const { session_token, user } = await auth.google(idToken)
      signIn(session_token, user)
      navigate(dest, { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Google sign-in failed.')
    }
  }

  return (
    <AuthCard
      title="Welcome back"
      subtitle="Log in to your EchoNotes courses."
      footer={
        <>
          New to EchoNotes?{' '}
          <Link to="/signup" className="font-medium text-brand-600 hover:underline dark:text-brand-400">
            Create an account
          </Link>
        </>
      }
    >
      <form onSubmit={submit} className="space-y-4">
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
        <div>
          <div className="mb-1.5 flex items-center justify-between">
            <label htmlFor="password" className="text-sm font-medium text-slate-700 dark:text-slate-300">
              Password
            </label>
            <Link
              to="/forgot-password"
              className="text-xs font-medium text-brand-600 hover:underline dark:text-brand-400"
            >
              Forgot password?
            </Link>
          </div>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
          />
        </div>
        <FormError message={error} />
        <Button type="submit" disabled={busy} className="w-full">
          {busy ? 'Logging in…' : 'Log in'}
        </Button>
      </form>

      <GoogleButton onCredential={onGoogle} onError={setError} />
    </AuthCard>
  )
}
