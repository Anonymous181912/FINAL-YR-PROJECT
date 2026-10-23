import { Component } from 'react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error) {
    // Log for diagnostics without exposing internals to the user.
    if (typeof console !== 'undefined' && console.error) {
      console.error('Application error:', error?.message || error)
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 24,
          background: 'var(--slate-50)',
        }}>
          <div className="card" style={{ maxWidth: 440, textAlign: 'center', marginBottom: 0 }}>
            <h2 style={{ marginBottom: 8 }}>Something went wrong.</h2>
            <p style={{ color: 'var(--slate-500)', fontSize: '0.92rem', marginBottom: 20 }}>
              The application hit an unexpected error and could not continue on this page.
            </p>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'center', flexWrap: 'wrap' }}>
              <button className="btn btn-primary" onClick={() => window.location.reload()}>
                Reload application
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => {
                  localStorage.removeItem('user')
                  localStorage.removeItem('access_token')
                  window.location.href = '/login'
                }}
              >
                Return to Login
              </button>
            </div>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
