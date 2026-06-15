import { apiUrl } from '@/lib/http'

/** Turn a backend "/assets/…" path into a URL the browser can load. */
export function resolveAssetUrl(ref: string | null | undefined): string | undefined {
  if (!ref) return undefined
  if (/^https?:\/\//i.test(ref)) return ref
  return apiUrl(ref.startsWith('/') ? ref : `/${ref}`)
}
