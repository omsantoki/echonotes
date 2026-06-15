import { useEffect, useLayoutEffect, useRef } from 'react'

// Google Identity Services — loaded only when a client id is configured. With
// VITE_GOOGLE_CLIENT_ID blank the button renders nothing (the backend also 503s
// /api/auth/google), so local dev needs no Google setup (feature 002, Art. X).
const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID ?? ''
const GIS_SRC = 'https://accounts.google.com/gsi/client'

interface GoogleId {
  initialize: (opts: {
    client_id: string
    callback: (resp: { credential: string }) => void
  }) => void
  renderButton: (el: HTMLElement, opts: Record<string, unknown>) => void
}
declare global {
  interface Window {
    google?: { accounts: { id: GoogleId } }
  }
}

let scriptPromise: Promise<void> | null = null
function loadGis(): Promise<void> {
  if (scriptPromise) return scriptPromise
  scriptPromise = new Promise((resolve, reject) => {
    if (window.google?.accounts?.id) return resolve()
    const s = document.createElement('script')
    s.src = GIS_SRC
    s.async = true
    s.defer = true
    s.onload = () => resolve()
    s.onerror = () => reject(new Error('Failed to load Google sign-in'))
    document.head.appendChild(s)
  })
  return scriptPromise
}

export function GoogleButton({
  onCredential,
  onError,
}: {
  onCredential: (idToken: string) => void
  onError?: (message: string) => void
}) {
  const ref = useRef<HTMLDivElement>(null)
  // Keep the latest callbacks in refs so the init effect can run exactly ONCE —
  // otherwise it re-initializes GIS on every parent re-render (e.g. each keystroke).
  const onCredentialRef = useRef(onCredential)
  const onErrorRef = useRef(onError)
  useLayoutEffect(() => {
    onCredentialRef.current = onCredential
    onErrorRef.current = onError
  })

  useEffect(() => {
    if (!CLIENT_ID || !ref.current) return
    let cancelled = false
    loadGis()
      .then(() => {
        if (cancelled || !ref.current || !window.google) return
        window.google.accounts.id.initialize({
          client_id: CLIENT_ID,
          callback: (resp) => onCredentialRef.current(resp.credential),
        })
        window.google.accounts.id.renderButton(ref.current, {
          theme: 'outline',
          size: 'large',
          width: 320,
          text: 'continue_with',
        })
      })
      .catch((e) => onErrorRef.current?.(e instanceof Error ? e.message : 'Google sign-in unavailable'))
    return () => {
      cancelled = true
    }
  }, [])

  if (!CLIENT_ID) return null

  return (
    <div className="mt-5">
      <div className="mb-4 flex items-center gap-3 text-xs text-slate-400 dark:text-slate-500">
        <span className="h-px flex-1 bg-slate-200 dark:bg-slate-800" />
        or
        <span className="h-px flex-1 bg-slate-200 dark:bg-slate-800" />
      </div>
      <div ref={ref} className="flex justify-center" />
    </div>
  )
}

/** Whether Google sign-in is configured (used to decide whether to show dividers etc.). */
export const googleEnabled = Boolean(CLIENT_ID)
