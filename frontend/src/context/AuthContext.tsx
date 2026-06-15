import {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { auth as authApi } from '@/lib/api'
import { ApiRequestError } from '@/lib/http'
import { clearToken, getToken, setToken, subscribe } from '@/lib/session'
import type { User } from '@/types/api'

export interface AuthContextValue {
  user: User | null
  /** True only while the initial /me bootstrap is in flight. */
  loading: boolean
  isAuthenticated: boolean
  /** Persist a session returned by login/signup/google and set the current user. */
  signIn: (token: string, user: User) => void
  /** Clear the session + cached per-user data. */
  signOut: () => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient()
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState<boolean>(() => Boolean(getToken()))

  // Bootstrap: if we have a token, confirm it with /me (and load the user).
  useEffect(() => {
    let cancelled = false
    if (!getToken()) {
      setLoading(false)
      return
    }
    authApi
      .me()
      .then((u) => {
        if (!cancelled) setUser(u)
      })
      .catch((err) => {
        // Only drop the session on a real 401 (expired/invalid token). A network
        // blip or backend hiccup must NOT log the user out — keep the token so a
        // reload can recover. (http.ts excludes /api/auth/* from its 401 auto-clear.)
        if (err instanceof ApiRequestError && err.status === 401) clearToken()
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  // React if the token is cleared elsewhere (e.g. a 401 inside http.ts): drop the
  // user so the route guards send them to /login, and forget any cached tenant data.
  useEffect(
    () =>
      subscribe(() => {
        if (!getToken()) {
          setUser(null)
          qc.clear()
        }
      }),
    [qc],
  )

  const signIn = useCallback(
    (token: string, u: User) => {
      qc.clear() // never show a previous user's cached courses/lectures
      setToken(token)
      setUser(u)
    },
    [qc],
  )

  const signOut = useCallback(() => {
    clearToken()
    setUser(null)
    qc.clear()
  }, [qc])

  const value = useMemo<AuthContextValue>(
    () => ({ user, loading, isAuthenticated: Boolean(user), signIn, signOut }),
    [user, loading, signIn, signOut],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
