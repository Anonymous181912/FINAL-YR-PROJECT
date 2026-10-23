import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../auth.jsx'
import {
  Sparkles,
  Stethoscope,
  User,
  Mail,
  Lock,
  ArrowRight,
  ShieldCheck,
  FileSearch,
  Pill,
  Activity,
  Eye,
  EyeOff
} from 'lucide-react'

export default function Login() {
  const [mode, setMode] = useState('login') // 'login' | 'register'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [licenseNumber, setLicenseNumber] = useState('')
  const [role, setRole] = useState('patient')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const { login, user } = useAuth()

  // Already authenticated (e.g. valid restored session): never show the
  // login form, go straight to the role dashboard.
  if (user) return <Navigate to="/dashboard" replace />

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setNotice('')
    setLoading(true)
    try {
      if (mode === 'register') {
        // Phase 0a: JSON-body registration (password policy enforced server-side).
        const body = { email, password, role, full_name: fullName }
        if (role === 'doctor' && licenseNumber.trim()) body.license_number = licenseNumber.trim()
        const response = await fetch('/api/v1/auth/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        const data = await response.json().catch(() => ({}))
        if (!response.ok) {
          const detail = Array.isArray(data.detail)
            ? data.detail.map((d) => d.msg).join('; ')
            : (data.detail || 'Registration failed')
          throw new Error(detail)
        }
        localStorage.setItem('access_token', data.access_token)
        login({ user_id: data.user_id, email, role: data.role || role, full_name: data.full_name, refresh_token: data.refresh_token })
        if (data.role === 'doctor') {
          setNotice('Doctor account created. It is pending admin approval before patient data is accessible.')
        }
        window.location.href = '/'
        return
      }
      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ username: email, password, grant_type: 'password' }),
      })
      if (!response.ok) throw new Error('Invalid email or password')
      const data = await response.json()
      localStorage.setItem('access_token', data.access_token)
      // Role is server truth: the backend returns the registered role for these
      // credentials. Never trust the portal toggle for authorization state.
      login({ user_id: data.user_id, email, role: data.role || role, full_name: data.full_name, refresh_token: data.refresh_token })
      window.location.href = '/'
    } catch (err) {
      setError(err.message || (mode === 'register' ? 'Registration failed.' : 'Login failed. Please check your credentials.'))
    } finally {
      setLoading(false)
    }
  }

  // Quick fill helper switches portal theme only; credentials stay user-entered
  const handleQuickRole = (selectedRole) => {
    setRole(selectedRole)
  }

  return (
    <div className="auth-page-container">
      {/* Left Feature Showcase Hero Pane */}
      <div className="auth-hero-pane">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div className="sidebar-logo-icon" style={{ width: 44, height: 44 }}>
            <Sparkles size={24} />
          </div>
          <div>
            <h2 style={{ color: 'white', fontSize: '1.25rem' }}>MediReport AI</h2>
            <span style={{ color: 'var(--teal-200)', fontSize: '0.78rem', letterSpacing: '0.06em', textTransform: 'uppercase', fontWeight: 600 }}>
              Clinical Intelligence System
            </span>
          </div>
        </div>

        <div style={{ maxWidth: 520, margin: '40px 0' }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            background: 'rgba(14, 165, 233, 0.15)',
            border: '1px solid rgba(14, 165, 233, 0.3)',
            borderRadius: 'var(--radius-full)',
            padding: '4px 12px',
            color: 'var(--primary-200)',
            fontSize: '0.8rem',
            fontWeight: 600,
            marginBottom: 16
          }}>
            <Activity size={14} />
            <span>Final Year Engineering Capstone</span>
          </div>

          <h1 style={{ color: 'white', fontSize: '2.4rem', lineHeight: 1.15, marginBottom: 16, fontFamily: 'var(--font-heading)' }}>
            Intelligent Medical Report Interpretation & Healthcare Platform
          </h1>

          <p style={{ color: 'var(--slate-300)', fontSize: '1.05rem', lineHeight: 1.6, marginBottom: 32 }}>
            Bridging patients and doctors with OCR extraction, rule-based clinical NLP, and patient-friendly AI interpretations.
          </p>

          {/* Feature Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div style={{ background: 'rgba(255, 255, 255, 0.04)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: 'var(--radius-md)', padding: 16 }}>
              <FileSearch size={22} color="#38bdf8" style={{ marginBottom: 8 }} />
              <h4 style={{ color: 'white', fontSize: '0.95rem', marginBottom: 4 }}>Multimodal OCR & NLP</h4>
              <p style={{ color: 'var(--slate-400)', fontSize: '0.82rem', lineHeight: 1.4 }}>
                Instant text extraction from PDF, PNG, JPG and automated clinical entity recognition.
              </p>
            </div>

            <div style={{ background: 'rgba(255, 255, 255, 0.04)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: 'var(--radius-md)', padding: 16 }}>
              <Sparkles size={22} color="#2dd4bf" style={{ marginBottom: 8 }} />
              <h4 style={{ color: 'white', fontSize: '0.95rem', marginBottom: 4 }}>AI Report Interpreter</h4>
              <p style={{ color: 'var(--slate-400)', fontSize: '0.82rem', lineHeight: 1.4 }}>
                Simplifies complex lab metrics and values into clear, structured explanations.
              </p>
            </div>

            <div style={{ background: 'rgba(255, 255, 255, 0.04)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: 'var(--radius-md)', padding: 16 }}>
              <Pill size={22} color="#a78bfa" style={{ marginBottom: 8 }} />
              <h4 style={{ color: 'white', fontSize: '0.95rem', marginBottom: 4 }}>Digital Prescriptions</h4>
              <p style={{ color: 'var(--slate-400)', fontSize: '0.82rem', lineHeight: 1.4 }}>
                Doctor-authored prescriptions with instant PDF generation and patient history.
              </p>
            </div>

            <div style={{ background: 'rgba(255, 255, 255, 0.04)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: 'var(--radius-md)', padding: 16 }}>
              <ShieldCheck size={22} color="#4ade80" style={{ marginBottom: 8 }} />
              <h4 style={{ color: 'white', fontSize: '0.95rem', marginBottom: 4 }}>Strict Safety Boundaries</h4>
              <p style={{ color: 'var(--slate-400)', fontSize: '0.82rem', lineHeight: 1.4 }}>
                Explains medical reports without generating unverified diagnoses or treatment claims.
              </p>
            </div>
          </div>
        </div>

        <div style={{ color: 'var(--slate-400)', fontSize: '0.78rem' }}>
          Final Year Engineering Project &copy; {new Date().getFullYear()} &bull; Fast-API + React + MongoDB
        </div>
      </div>

      {/* Right Login Form Pane */}
      <div className="auth-form-pane">
        <div className="auth-card">
          <div style={{ marginBottom: 28 }}>
            <h2 style={{ color: 'white', fontSize: '1.65rem', marginBottom: 6 }}>{mode === 'register' ? 'Create your account' : 'Welcome back'}</h2>
            <p style={{ color: 'var(--slate-400)', fontSize: '0.92rem' }}>
              {mode === 'register' ? 'Register for a patient or doctor portal' : 'Select your role and sign in to your portal'}
            </p>
          </div>

          {/* Role Switcher Pills */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: 8,
            background: 'rgba(255, 255, 255, 0.05)',
            padding: 4,
            borderRadius: 'var(--radius-md)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            marginBottom: 20
          }}>
            <button
              type="button"
              onClick={() => handleQuickRole('patient')}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8,
                padding: '9px 12px',
                borderRadius: 'var(--radius-sm)',
                border: 'none',
                background: role === 'patient' ? 'linear-gradient(135deg, var(--teal-500), var(--teal-600))' : 'transparent',
                color: role === 'patient' ? 'white' : 'var(--slate-400)',
                fontWeight: 600,
                fontSize: '0.88rem',
                cursor: 'pointer',
                transition: 'all 0.2s'
              }}
            >
              <User size={16} />
              <span>Patient Portal</span>
            </button>

            <button
              type="button"
              onClick={() => handleQuickRole('doctor')}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8,
                padding: '9px 12px',
                borderRadius: 'var(--radius-sm)',
                border: 'none',
                background: role === 'doctor' ? 'linear-gradient(135deg, var(--primary-500), var(--primary-600))' : 'transparent',
                color: role === 'doctor' ? 'white' : 'var(--slate-400)',
                fontWeight: 600,
                fontSize: '0.88rem',
                cursor: 'pointer',
                transition: 'all 0.2s'
              }}
            >
              <Stethoscope size={16} />
              <span>Doctor Portal</span>
            </button>
          </div>

          {error && (
            <div style={{
              background: 'rgba(239, 68, 68, 0.15)',
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

          {notice && (
            <div style={{
              background: 'rgba(20, 184, 166, 0.15)',
              border: '1px solid rgba(20, 184, 166, 0.3)',
              borderRadius: 'var(--radius-md)',
              padding: '12px 14px',
              color: '#5eead4',
              fontSize: '0.86rem',
              marginBottom: 20
            }}>
              {notice}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            {mode === 'register' && (
              <div className="form-group">
                <label style={{ color: 'var(--slate-300)' }}>Full Name</label>
                <div style={{ position: 'relative' }}>
                  <input
                    type="text"
                    value={fullName}
                    onChange={e => setFullName(e.target.value)}
                    placeholder="Your full name"
                    required
                    minLength={2}
                    style={{
                      background: 'rgba(255, 255, 255, 0.05)',
                      borderColor: 'rgba(255, 255, 255, 0.15)',
                      color: 'white',
                      paddingLeft: 40
                    }}
                  />
                  <User size={16} style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: 'var(--slate-400)' }} />
                </div>
              </div>
            )}

            <div className="form-group">
              <label style={{ color: 'var(--slate-300)' }}>Email Address</label>
              <div style={{ position: 'relative' }}>
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="name@example.com"
                  required
                  style={{
                    background: 'rgba(255, 255, 255, 0.05)',
                    borderColor: 'rgba(255, 255, 255, 0.15)',
                    color: 'white',
                    paddingLeft: 40
                  }}
                />
                <Mail size={16} style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: 'var(--slate-400)' }} />
              </div>
            </div>

            <div className="form-group">
              <label style={{ color: 'var(--slate-300)' }}>Password</label>
              <div style={{ position: 'relative' }}>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  required
                  style={{
                    background: 'rgba(255, 255, 255, 0.05)',
                    borderColor: 'rgba(255, 255, 255, 0.15)',
                    color: 'white',
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
              {mode === 'register' && (
                <p style={{ color: 'var(--slate-400)', fontSize: '0.76rem', marginTop: 6 }}>
                  Min 8 characters, with at least one letter and one digit.
                </p>
              )}
              {mode === 'login' && (
                <p style={{ marginTop: 6, textAlign: 'right' }}>
                  <a href="/forgot-password" style={{ fontSize: '0.78rem', color: 'var(--primary-200)' }}>
                    Forgot password?
                  </a>
                </p>
              )}
            </div>

            {mode === 'register' && role === 'doctor' && (
              <div className="form-group">
                <label style={{ color: 'var(--slate-300)' }}>Medical License Number (optional)</label>
                <input
                  type="text"
                  value={licenseNumber}
                  onChange={e => setLicenseNumber(e.target.value)}
                  placeholder="e.g. MCI-12345"
                  style={{
                    background: 'rgba(255, 255, 255, 0.05)',
                    borderColor: 'rgba(255, 255, 255, 0.15)',
                    color: 'white',
                  }}
                />
                <p style={{ color: 'var(--slate-400)', fontSize: '0.76rem', marginTop: 6 }}>
                  Doctor accounts require admin approval before accessing patient data.
                </p>
              </div>
            )}

            <button
              type="submit"
              className={role === 'doctor' ? 'btn btn-primary' : 'btn btn-teal'}
              style={{ width: '100%', marginTop: 8, padding: '12px' }}
              disabled={loading}
            >
              {loading ? (
                <span>{mode === 'register' ? 'Creating account...' : 'Signing in...'}</span>
              ) : (
                <>
                  <span>{mode === 'register' ? `Create ${role === 'doctor' ? 'Doctor' : 'Patient'} Account` : `Sign In as ${role === 'doctor' ? 'Doctor' : 'Patient'}`}</span>
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          </form>

          <div style={{ textAlign: 'center', marginTop: 16 }}>
            <button
              type="button"
              onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(''); setNotice('') }}
              style={{ background: 'transparent', border: 'none', color: 'var(--primary-200)', cursor: 'pointer', fontSize: '0.85rem', fontWeight: 600 }}
            >
              {mode === 'login' ? 'New here? Create an account' : 'Already have an account? Sign in'}
            </button>
          </div>

          {/* Quick Demo Credentials Footer */}
          <div style={{
            marginTop: 24,
            paddingTop: 20,
            borderTop: '1px solid rgba(255, 255, 255, 0.1)',
            textAlign: 'center'
          }}>
            <p style={{ color: 'var(--slate-400)', fontSize: '0.8rem', marginBottom: 8 }}>
              Choose a portal:
            </p>
            <div style={{ display: 'flex', justifyContent: 'center', gap: 8 }}>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                style={{ color: 'var(--teal-200)', border: '1px solid rgba(20, 184, 166, 0.3)', fontSize: '0.75rem' }}
                onClick={() => handleQuickRole('patient')}
              >
                Patient Portal
              </button>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                style={{ color: 'var(--primary-200)', border: '1px solid rgba(14, 165, 233, 0.3)', fontSize: '0.75rem' }}
                onClick={() => handleQuickRole('doctor')}
              >
                Doctor Portal
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
