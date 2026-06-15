import { useEffect, useState } from 'react'
import { applyTheme, resolveTheme, type Theme } from '@/lib/theme'

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(() => resolveTheme())
  useEffect(() => {
    applyTheme(theme)
  }, [theme])
  return {
    theme,
    toggle: () => setTheme((t) => (t === 'dark' ? 'light' : 'dark')),
  }
}
