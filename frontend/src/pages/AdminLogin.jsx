import { useState } from 'react'
import { Navigate, Link } from 'react-router-dom'
import { useAuth } from '../auth.jsx'
import {
  ShieldCheck,
  Mail,
  Lock,
  ArrowRight,
  Eye,
  EyeOff,
  KeyRound,
} from 'lucide-react'

export default function AdminLogin() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const { login } = useAuth()

  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('access_token')
    const userStr = localStorage.getItem('user')
    if (token && userStr) {
      try {
        const user = JSON.parse(userStr)
        if (user.role === 'admin') return <Navigate to="/admin" replace />
      } catch {}
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ username: email, password, portal: 'admin', grant_type: 'password' }),
      })
      if (!response.ok) throw new Error('Invalid email or password')
      const data = await response.json()
      localStorage.setItem('access_token', data.access_token)
      login({ user_id: data.user_id, email, role: data.role, full_name: data.full_name, refresh_token: data.refresh_token })
      window.location.href = '/admin/dashboard'
    } catch (err) {
      setError(err.message || 'Login failed. Please check your credentials.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page-container">
      {/* Left Feature Showcase Hero Pane */}
      <div className="auth-hero-pane" style={{ background: 'linear-gradient(135deg, var(--slate-800), var(--slate-900))' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div className="sidebar-logo-icon" style={{ width: 44, height: 44 }}>
            <KeyRound size={24} color="#fbbf24" />
          </div>
          <div>
            <h2 style={{ color: 'white', fontSize: '1.25rem' }}>MediReport AI</h2>
            <span style={{ color: '#fde68a', fontSize: '0.78rem', letterSpacing: '0.06em', textTransform: 'uppercase', fontWeight: 600 }}>
              Admin Console
            </span>
          </div>
        </div>

        <div style={{ maxWidth: 520, margin: '40px 0' }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            background: 'rgba(251, 191, 36, 0.15)',
            border: '1px solid rgba(251, 191, 36, 0.3)',
            borderRadius: 'var(--radius-full)',
            padding: '4px 12px',
            color: '#fbbf24',
            fontSize: '0.8rem',
            fontWeight: 600,
            marginBottom: 16
          }}>
            <ShieldCheck size={14} />
            <span>Administrative Access Only</span>
          </div>

          <h1 style={{ color: 'white', fontSize: '2.4rem', lineHeight: 1.15, marginBottom: 16, fontFamily: 'var(--font-heading)' }}>
            Administration Portal
          </h1>

          <p style={{ color: 'rgba(255,255,255,0.9)', fontSize: '1.05rem', lineHeight: 1.6, marginBottom: 32 }}>
            Manage doctor verifications, audit logs, and system configuration.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div style={{ background: 'rgba(255, 255, 255, 0.04)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: 'var(--radius-md)', padding: 16 }}>
              <ShieldCheck size={22} color="#fbbf24" style={{ marginBottom: 8 }} />
              <h4 style={{ color: 'white', fontSize: '0.95rem', marginBottom: 4 }}>Doctor Verification</h4>
              <p style={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.82rem', lineHeight: 1.4 }}>
                Approve or reject doctor registration requests.
              </p>
            </div>

            <div style={{ background: 'rgba(255, 255, 255, 0.04)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: 'var(--radius-md)', padding: 16 }}>
              <KeyRound size={22} color="#fbbf24" style={{ marginBottom: 8 }} />
              <h4 style={{ color: 'white', fontSize: '0.95rem', marginBottom: 4 }}>Audit Logs</h4>
              <p style={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.82rem', lineHeight: 1.4 }}>
                Review all system access and clinical actions.
              </p>
            </div>
          </div>
        </div>

        <div style={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.78rem' }}>
          Final Year Engineering Project &copy; {new Date().getFullYear()} &bull; FastAPI + React + MongoDB
        </div>
      </div>

      {/* Right Login Form Pane */}
      <div className="auth-form-pane">
        <div className="auth-card">
          <div style={{ marginBottom: 28 }}>
            <h2 style={{ color: 'var(--slate-900)', fontSize: '1.65rem', marginBottom: 6 }}>
              Admin Sign In
            </h2>
            <p style={{ color: 'var(--slate-500)', fontSize: '0.92rem' }}>
              Enter your admin credentials to access the console
            </p>
          </div>

          {error && (
            <div style={{
              background: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: 'var(--radius-md)',
              padding: '12px 14px',
              color: '#fca5a5',
              fontSize: '0.86rem',
              marginBottom: 20
            }}>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label style={{ color: 'var(--slate-600)' }}>Email Address</label>
              <div style={{ position: 'relative' }}>
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="admin@hospital.com"
                  required
                  style={{
                    background: 'var(--slate-50)',
                    borderColor: 'var(--slate-200)',
                    color: 'var(--slate-900)',
                    paddingLeft: 40
                  }}
                />
                <Mail size={16} style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: 'var(--slate-400)' }} />
              </div>
            </div>

            <div className="form-group">
              <label style={{ color: 'var(--slate-600)' }}>Password</label>
              <div style={{ position: 'relative' }}>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  required
                  style={{
                    background: 'var(--slate-50)',
                    borderColor: 'var(--slate-200)',
                    color: 'var(--slate-900)',
                    paddingLeft: 40,
                    paddingRight: 40
                  }}
                />
                <Lock size={16} style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: 'var(--slate-400)' }} />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', background: 'transparent', border: 'none', color: 'var(--slate-400)', cursor: 'pointer' }}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              style={{ width: '100%', marginTop: 8, padding: '12px' }}
              disabled={loading}
            >
              {loading ? (
                <span>Signing in...</span>
              ) : (
                <>
                  <span>Access Admin Console</span>
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          </form>

          <div style={{ textAlign: 'center', marginTop: 24, paddingTop: 20, borderTop: '1px solid var(--slate-200)' }}>
            <p style={{ color: 'var(--slate-500)', fontSize: '0.8rem' }}>
              <Link to="/patient/login" style={{ color: 'var(--teal-600)', fontWeight: 600 }}>Patient Portal</Link> &bull; 
              <Link to="/doctor/login" style={{ color: 'var(--primary-600)', fontWeight: 600 }}>Doctor Portal</Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}