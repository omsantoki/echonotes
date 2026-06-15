import type { ApiError } from '@/types/api'

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

export async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(apiUrl(path), { headers: { Accept: 'application/json' } })
  if (!res.ok) throw await toError(res)
  return (await res.json()) as T
}

export async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(apiUrl(path), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw await toError(res)
  return (await res.json()) as T
}

export async function del(path: string): Promise<void> {
  const res = await fetch(apiUrl(path), {
    method: 'DELETE',
    headers: { Accept: 'application/json' },
  })
  if (!res.ok) throw await toError(res)
}
