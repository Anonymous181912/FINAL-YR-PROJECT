/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: ['class', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        background: 'var(--bg)',
        surface: {
          DEFAULT: 'var(--surface)',
          2: 'var(--surface-2)',
        },
        border: 'var(--border)',
        foreground: {
          DEFAULT: 'var(--text)',
          muted: 'var(--text-muted)',
          subtle: 'var(--text-subtle)',
        },
        accent: {
          DEFAULT: 'var(--accent)',
          hover: 'var(--accent-hover)',
          soft: 'var(--accent-soft)',
          foreground: 'var(--on-accent)',
        },
        status: {
          success: {
            DEFAULT: 'var(--success-fg)',
            bg: 'var(--success-bg)',
            border: 'var(--success-border)',
          },
          warning: {
            DEFAULT: 'var(--warning-fg)',
            bg: 'var(--warning-bg)',
            border: 'var(--warning-border)',
          },
          danger: {
            DEFAULT: 'var(--danger-fg)',
            bg: 'var(--danger-bg)',
            border: 'var(--danger-border)',
          },
          info: {
            DEFAULT: 'var(--info-fg)',
            bg: 'var(--info-bg)',
            border: 'var(--info-border)',
          },
        },
        sidebar: {
          DEFAULT: 'var(--sidebar-bg)',
          surface: 'var(--sidebar-surface)',
          border: 'var(--sidebar-border)',
          foreground: 'var(--sidebar-text)',
          muted: 'var(--sidebar-text-muted)',
          active: 'var(--sidebar-active-bg)',
          'active-text': 'var(--sidebar-active-text)',
        },
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        heading: ['Manrope', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      borderRadius: {
        card: '16px',
        item: '12px',
      },
      boxShadow: {
        subtle: 'var(--shadow-subtle)',
        card: 'var(--shadow-card)',
        dropdown: 'var(--shadow-dropdown)',
      },
      maxWidth: {
        container: '1200px',
      },
    },
  },
  plugins: [],
}
