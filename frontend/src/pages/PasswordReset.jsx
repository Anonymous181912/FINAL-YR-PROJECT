import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

export function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [done, setDone] = useState(false)
  const [loading, setLoading] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await fetch('/api/v1/auth/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })
    } catch { /* always show the same message */ }
    setDone(true)
    setLoading(false)
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
      <div className="card" style={{ maxWidth: 420, width: '100%' }}>
        <h2>Reset password</h2>
        {done ? (
          <p style={{ color: 'var(--slate-600)', fontSize: '0.9rem' }}>
            If the email is registered, a reset link has been sent. Check your inbox
            (in this demo setup, ask the administrator for the link).
          </p>
        ) : (
          <form onSubmit={submit}>
            <div className="form-group">
              <label htmlFor="forgot-email">Email address</label>
              <input
                id="forgot-email" type="email" value={email}
                onChange={(e) => setEmail(e.target.value)} required
                placeholder="name@example.com"
              />
            </div>
            <button type="submit" className="btn btn-primary" disabled={loading} style={{ width: '100%' }}>
              {loading ? 'Sending...' : 'Send reset link'}
            </button>
          </form>
        )}
        <div style={{ marginTop: 12, textAlign: 'center' }}>
          <Link to="/login" style={{ fontSize: '0.85rem' }}>Back to sign in</Link>
        </div>
      </div>
    </div>
  )
}

export function ResetPassword() {
  const [params] = useSearchParams()
  const token = params.get('token') || ''
  const [password, setPassword] = useState('')
  const [msg, setMsg] = useState('')
  const [ok, setOk] = useState(false)
  const [loading, setLoading] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setMsg('')
    try {
      const res = await fetch('/api/v1/auth/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, new_password: password }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.detail || 'Reset failed')
      setOk(true)
      setMsg('Password changed. You can now sign in.')
    } catch (err) {
      setMsg(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
      <div className="card" style={{ maxWidth: 420, width: '100%' }}>
        <h2>Choose a new password</h2>
        <p style={{ fontSize: '0.82rem', color: 'var(--slate-500)' }}>
          Minimum 8 characters, with at least one letter and one digit.
        </p>
        {ok ? (
          <p style={{ color: '#166534' }}>{msg} <Link to="/login">Sign in</Link></p>
        ) : (
          <form onSubmit={submit}>
            <div className="form-group">
              <label htmlFor="new-password">New password</label>
              <input
                id="new-password" type="password" value={password}
                onChange={(e) => setPassword(e.target.value)} required minLength={8}
              />
            </div>
            {msg && <p style={{ color: '#b91c1c', fontSize: '0.85rem' }}>{msg}</p>}
            <button type="submit" className="btn btn-primary" disabled={loading || !token} style={{ width: '100%' }}>
              {loading ? 'Saving...' : 'Change password'}
            </button>
            {!token && <p style={{ color: '#b91c1c', fontSize: '0.85rem' }}>Missing reset token in the link.</p>}
          </form>
        )}
      </div>
    </div>
  )
}
