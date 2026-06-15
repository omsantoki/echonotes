import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { CheckCircle2 } from 'lucide-react'
import { auth } from '@/lib/api'
import { AuthCard, Field, FormError } from '@/components/auth/AuthCard'
import { Button } from '@/components/ui/Button'

export function ResetPasswordPage() {
  const [params] = useSearchParams()
  const token = params.get('token') ?? ''
  const navigate = useNavigate()

  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [done, setDone] = useState(false)
  const [error, setError] = useState<string>()
  const [busy, setBusy] = useState(false)

  const footer = (
    <Link to="/login" className="font-medium text-brand-600 hover:underline dark:text-brand-400">
      Back to log in
    </Link>
  )

  if (!token) {
    return (
      <AuthCard title="Invalid reset link" footer={footer}>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          This link is missing its token. Request a new link from the{' '}
          <Link to="/forgot-password" className="font-medium text-brand-600 hover:underline dark:text-brand-400">
            forgot-password page
          </Link>
          .
        </p>
      </AuthCard>
    )
  }

  if (done) {
    return (
      <AuthCard title="Password updated" footer={footer}>
        <div className="flex flex-col items-center gap-3 py-2 text-center">
          <CheckCircle2 className="h-10 w-10 text-emerald-500" />
          <p className="text-sm text-slate-600 dark:text-slate-300">
            Your password has been changed. You can now log in with it.
          </p>
          <Button onClick={() => navigate('/login')} className="mt-1">
            Go to log in
          </Button>
        </div>
      </AuthCard>
    )
  }

  async function submit(e: FormEvent) {
    e.preventDefault()
    setError(undefined)
    if (password !== confirm) {
      setError('Passwords do not match.')
      return
    }
    setBusy(true)
    try {
      await auth.resetPassword(token, password)
      setDone(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not reset your password.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthCard title="Choose a new password" footer={footer}>
      <form onSubmit={submit} className="space-y-4">
        <Field
          label="New password"
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
          label="Confirm new password"
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
          {busy ? 'Updating…' : 'Update password'}
        </Button>
      </form>
    </AuthCard>
  )
}
