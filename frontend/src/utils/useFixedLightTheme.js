import { useLayoutEffect } from 'react'

// Public pages (landing + auth) always use their fixed light theme. This clears
// any dark theme left on <html> by a portal layout or the OS preference.
export function useFixedLightTheme() {
  useLayoutEffect(() => {
    const root = document.documentElement
    root.setAttribute('data-theme', 'light')
    root.classList.remove('dark')
  }, [])
}
