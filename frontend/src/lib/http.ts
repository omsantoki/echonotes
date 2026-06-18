import type { ApiError } from '@/types/api'
import { clearToken, getToken } from '@/lib/session'

// In dev VITE_API_BASE is blank (the Vite proxy forwards same-origin /api and
// /assets to FastAPI). In prod it's the backend origin. No trailing slash.
const BASE = (import.meta.env.VITE_API_BASE ?? '').replace(/\/$/, '')

export class ApiRequestError extends Error {
  code: string
  status: number
  constructor(message: string, code: string, status: number) {
    super(message)
    this.name = 'ApiRequestError'
    this.code = code
    this.status = status
  }
}

export function apiUrl(path: string): string {
  return `${BASE}${path}`
}

// Authorization: Bearer <jwt> on every call when we have a session (feature 002).
function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = { Accept: 'application/json', ...extra }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  return headers
}

async function toError(res: Response): Promise<ApiRequestError> {
  let code = 'error'
  let message = res.statusText || 'Request failed'
  try {
    const body = (await res.json()) as ApiError
    if (body?.error) {
      code = body.error.code ?? code
      message = body.error.message ?? message
    }
  } catch {
    /* non-JSON error body — keep the status text */
  }
  return new ApiRequestError(message, code, res.status)
}

// A 401 means the session is gone/expired: drop the token so the AuthContext +
// route guards send the user to /login. Auth endpoints opt out (a bad login is a
// 401 we want to surface inline, not a session expiry).
async function guard(res: Response, path: string): Promise<ApiRequestError> {
  if (res.status === 401 && !path.startsWith('/api/auth/')) clearToken()
  return toError(res)
}

export async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(apiUrl(path), { headers: authHeaders() })
  if (!res.ok) throw await guard(res, path)
  return (await res.json()) as T
}

export async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(apiUrl(path), {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(body),
  })
  if (!res.ok) throw await guard(res, path)
  return (await res.json()) as T
}

export async function del(path: string): Promise<void> {
  const res = await fetch(apiUrl(path), { method: 'DELETE', headers: authHeaders() })
  if (!res.ok) throw await guard(res, path)
}
