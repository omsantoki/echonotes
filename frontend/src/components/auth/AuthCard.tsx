import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { Logo } from '@/components/ui/Logo'

/** Shared shell for the auth pages — centered card matching the app's surface style. */
export function AuthCard({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string
  subtitle?: ReactNode
  children: ReactNode
  footer?: ReactNode
}) {
  return (
    <div className="mx-auto flex max-w-md flex-col px-4 py-14 sm:py-20">
      <div className="mb-8 flex justify-center">
        <Link to="/" aria-label="EchoNotes home">
          <Logo />
        </Link>
      </div>
      <div className="rounded-2xl border border-slate-200 bg-white p-7 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">{title}</h1>
        {subtitle && <p className="mt-1.5 text-sm text-slate-500 dark:text-slate-400">{subtitle}</p>}
        <div className="mt-6">{children}</div>
      </div>
      {footer && (
        <p className="mt-6 text-center text-sm text-slate-500 dark:text-slate-400">{footer}</p>
      )}
    </div>
  )
}

/** A labelled text/password input styled like the rest of the app's form fields. */
export function Field({
  label,
  id,
  ...rest
}: { label: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <div>
      <label
        htmlFor={id}
        className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300"
      >
        {label}
      </label>
      <input
        id={id}
        className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
        {...rest}
      />
    </div>
  )
}

/** Inline form error message. */
export function FormError({ message }: { message?: string }) {
  if (!message) return null
  return <p className="text-sm text-red-600 dark:text-red-400">{message}</p>
}
