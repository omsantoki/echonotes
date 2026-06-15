// Session token storage (feature 002). The JWT lives in localStorage; http.ts
// attaches it as a Bearer header and clears it on a 401. A tiny pub/sub lets the
// AuthContext react when the token is cleared out from under it (e.g. by a 401).

const KEY = 'echonotes-session'

type Listener = () => void
const listeners = new Set<Listener>()

export function getToken(): string | null {
  try {
    return localStorage.getItem(KEY)
  } catch {
    return null
  }
}

export function setToken(token: string): void {
  try {
    localStorage.setItem(KEY, token)
  } catch {
    /* storage unavailable (private mode) — session is in-memory for this tab only */
  }
  listeners.forEach((l) => l())
}

export function clearToken(): void {
  try {
    localStorage.removeItem(KEY)
  } catch {
    /* ignore */
  }
  listeners.forEach((l) => l())
}

/** Subscribe to token changes; returns an unsubscribe fn. */
export function subscribe(listener: Listener): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}
