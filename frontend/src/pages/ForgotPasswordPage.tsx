import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { MailCheck } from 'lucide-react'
import { auth } from '@/lib/api'
import { AuthCard, Field, FormError } from '@/components/auth/AuthCard'
import { Button } from '@/components/ui/Button'

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [error, setError] = useState<string>()
  const [busy, setBusy] = useState(false)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setError(undefined)
    setBusy(true)
    try {
      await auth.forgotPassword(email.trim())
      setSent(true) // response is neutral by design (no account-existence leak)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not send the reset link.')
    } finally {
      setBusy(false)
    }
  }

  const footer = (
    <Link to="/login" className="font-medium text-brand-600 hover:underline dark:text-brand-400">
      Back to log in
    </Link>
  )

  if (sent) {
    return (
      <AuthCard title="Check your email" footer={footer}>
        <div className="flex flex-col items-center gap-3 py-2 text-center">
          <MailCheck className="h-10 w-10 text-emerald-500" />
          <p className="text-sm text-slate-600 dark:text-slate-300">
            If an account exists for <span className="font-medium">{email}</span>, a password reset
            link is on its way. Check your inbox — and your spam folder.
          </p>
        </div>
      </AuthCard>
    )
  }

  return (
    <AuthCard
      title="Reset your password"
      subtitle="Enter your email and we'll send you a reset link."
      footer={footer}
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
        <FormError message={error} />
        <Button type="submit" disabled={busy} className="w-full">
          {busy ? 'Sending…' : 'Send reset link'}
        </Button>
      </form>
    </AuthCard>
  )
}
