/** 0.88 -> "88%" (matches render.py's ":.0%"). Empty string for non-numbers. */
export function percent(value: number | null | undefined): string {
  if (typeof value !== 'number' || Number.isNaN(value)) return ''
  return `${Math.round(value * 100)}%`
}

/** ISO date/datetime -> "14 Jun 2026"; falls back to the raw value. */
export function formatDate(value: string | null | undefined): string {
  if (!value) return ''
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}
