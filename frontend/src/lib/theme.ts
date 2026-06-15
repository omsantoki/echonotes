export type Theme = 'light' | 'dark'
const KEY = 'echonotes-theme'

export function getStoredTheme(): Theme | null {
  const t = localStorage.getItem(KEY)
  return t === 'dark' || t === 'light' ? t : null
}

export function resolveTheme(): Theme {
  return (
    getStoredTheme() ??
    (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
  )
}

export function applyTheme(theme: Theme): void {
  document.documentElement.classList.toggle('dark', theme === 'dark')
  localStorage.setItem(KEY, theme)
}
