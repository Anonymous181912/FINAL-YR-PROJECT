import { useState } from 'react'
import { Navigate, Link } from 'react-router-dom'
import { useAuth } from '../auth.jsx'
import {
  Sparkles,
  Mail,
  Lock,
  ArrowRight,
  ShieldCheck,
  FileSearch,
  Pill,
  Activity,
  Eye,
  EyeOff,
  HeartPulse,
  Users,
  User,
} from 'lucide-react'

const portalTheme = {
  patient: {
    primary: 'teal',
    gradient: 'from-teal-500 to-teal-600',
    bgGradient: 'from-teal-500 via-teal-600 to-cyan-600',
    accent: 'teal-500',
    icon: HeartPulse,
    title: 'Patient Portal',
    subtitle: 'Your Personal Health Management',
    description: 'Access your reports, prescriptions, and health timeline securely.',
  },
  doctor: {
    primary: 'primary',
    gradient: 'from-primary-500 to-primary-600',
    bgGradient: 'from-primary-500 via-primary-600 to-blue-600',
    accent: 'primary-500',
    icon: Sparkles,
    title: 'Doctor Portal',
    subtitle: 'Clinical Workspace',
    description: 'Manage patients, write prescriptions, and review clinical data.',
  },
}

export default function DoctorLogin({ mode: initialMode = 'login' }) {
  const theme = portalTheme.doctor
  const [mode, setMode] = useState(initialMode === 'register' ? 'register' : 'login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [licenseNumber, setLicenseNumber] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const { login } = useAuth()

  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('access_token')
    const userStr = localStorage.getItem('user')
    if (token && userStr) {
      try {
        const user = JSON.parse(userStr)
        if (user.role === 'doctor') return <Navigate to="/doctor/dashboard" replace />
      } catch {}
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setNotice('')
    setLoading(true)
    try {
      if (mode === 'register') {
        const body = { email, password, role: 'doctor', portal: 'doctor', full_name: fullName, license_number: licenseNumber }
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
        login({ user_id: data.user_id, email, role: 'doctor', full_name: data.full_name, refresh_token: data.refresh_token })
        window.location.href = '/doctor/dashboard'
        return
      }
      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ username: email, password, portal: 'doctor', grant_type: 'password' }),
      })
      if (!response.ok) throw new Error('Invalid email or password')
      const data = await response.json()
      localStorage.setItem('access_token', data.access_token)
      login({ user_id: data.user_id, email, role: data.role, full_name: data.full_name, refresh_token: data.refresh_token })
      window.location.href = '/doctor/dashboard'
    } catch (err) {
      setError(err.message || (mode === 'register' ? 'Registration failed.' : 'Login failed. Please check your credentials.'))
    } finally {
      setLoading(false)
    }
  }

  const Icon = theme.icon

  return (
    <div className="auth-page-container">
      {/* Left Feature Showcase Hero Pane */}
      <div className="auth-hero-pane" style={{ background: `linear-gradient(135deg, var(--${theme.accent}), var(--${theme.accent.replace('500', '600')}))` }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div className="sidebar-logo-icon" style={{ width: 44, height: 44 }}>
            <Icon size={24} />
          </div>
          <div>
            <h2 style={{ color: 'white', fontSize: '1.25rem' }}>MediReport AI</h2>
            <span style={{ color: 'var(--primary-200)', fontSize: '0.78rem', letterSpacing: '0.06em', textTransform: 'uppercase', fontWeight: 600 }}>
              {theme.subtitle}
            </span>
          </div>
        </div>

        <div style={{ maxWidth: 520, margin: '40px 0' }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            background: 'rgba(255, 255, 255, 0.15)',
            border: '1px solid rgba(255, 255, 255, 0.3)',
            borderRadius: 'var(--radius-full)',
            padding: '4px 12px',
            color: 'white',
            fontSize: '0.8rem',
            fontWeight: 600,
            marginBottom: 16
          }}>
            <Activity size={14} />
            <span>Verified Doctors Only</span>
          </div>

          <h1 style={{ color: 'white', fontSize: '2.4rem', lineHeight: 1.15, marginBottom: 16, fontFamily: 'var(--font-heading)' }}>
            {theme.title}
          </h1>

          <p style={{ color: 'rgba(255,255,255,0.9)', fontSize: '1.05rem', lineHeight: 1.6, marginBottom: 32 }}>
            {theme.description}
          </p>

          {/* Feature Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div style={{ background: 'rgba(255, 255, 255, 0.04)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: 'var(--radius-md)', padding: 16 }}>
              <Users size={22} color="white" style={{ marginBottom: 8 }} />
              <h4 style={{ color: 'white', fontSize: '0.95rem', marginBottom: 4 }}>Patient Directory</h4>
              <p style={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.82rem', lineHeight: 1.4 }}>
                Search and manage patients with access grants.
              </p>
            </div>

            <div style={{ background: 'rgba(255, 255, 255, 0.04)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: 'var(--radius-md)', padding: 16 }}>
              <Pill size={22} color="white" style={{ marginBottom: 8 }} />
              <h4 style={{ color: 'white', fontSize: '0.95rem', marginBottom: 4 }}>Write Prescriptions</h4>
              <p style={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.82rem', lineHeight: 1.4 }}>
                Create digital Rx with safety checks & PDF export.
              </p>
            </div>

            <div style={{ background: 'rgba(255, 255, 255, 0.04)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: 'var(--radius-md)', padding: 16 }}>
              <FileSearch size={22} color="white" style={{ marginBottom: 8 }} />
              <h4 style={{ color: 'white', fontSize: '0.95rem', marginBottom: 4 }}>Review Reports</h4>
              <p style={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.82rem', lineHeight: 1.4 }}>
                Access patient reports with AI interpretations.
              </p>
            </div>

            <div style={{ background: 'rgba(255, 255, 255, 0.04)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: 'var(--radius-md)', padding: 16 }}>
              <ShieldCheck size={22} color="white" style={{ marginBottom: 8 }} />
              <h4 style={{ color: 'white', fontSize: '0.95rem', marginBottom: 4 }}>Access Requests</h4>
              <p style={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.82rem', lineHeight: 1.4 }}>
                Manage patient consent for data access.
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
              {mode === 'register' ? 'Create your doctor account' : 'Welcome back, Doctor'}
            </h2>
            <p style={{ color: 'var(--slate-500)', fontSize: '0.92rem' }}>
              {mode === 'register' ? 'Register for clinical workspace access' : 'Sign in to your doctor portal'}
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

          {notice && (
            <div style={{
              background: 'rgba(14, 165, 233, 0.1)',
              border: '1px solid rgba(14, 165, 233, 0.3)',
              borderRadius: 'var(--radius-md)',
              padding: '12px 14px',
              color: '#7dd3fc',
              fontSize: '0.86rem',
              marginBottom: 20
            }}>
              {notice}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            {mode === 'register' && (
              <div className="form-group">
                <label style={{ color: 'var(--slate-600)' }}>Full Name</label>
                <div style={{ position: 'relative' }}>
                  <input
                    type="text"
                    value={fullName}
                    onChange={e => setFullName(e.target.value)}
                    placeholder="Dr. Your Name"
                    required
                    minLength={2}
                    style={{
                      background: 'var(--slate-50)',
                      borderColor: 'var(--slate-200)',
                      color: 'var(--slate-900)',
                      paddingLeft: 40
                    }}
                  />
                  <User size={16} style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: 'var(--slate-400)' }} />
                </div>
              </div>
            )}

            <div className="form-group">
              <label style={{ color: 'var(--slate-600)' }}>Email Address</label>
              <div style={{ position: 'relative' }}>
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="dr.name@clinic.com"
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
              {mode === 'register' && (
                <p style={{ color: 'var(--slate-500)', fontSize: '0.76rem', marginTop: 6 }}>
                  Min 8 characters, with at least one letter and one digit.
                </p>
              )}
              {mode === 'login' && (
                <p style={{ marginTop: 6, textAlign: 'right' }}>
                  <a href="/forgot-password" style={{ fontSize: '0.78rem', color: 'var(--primary-600)' }}>
                    Forgot password?
                  </a>
                </p>
              )}
            </div>

            {mode === 'register' && (
              <div className="form-group">
                <label style={{ color: 'var(--slate-600)' }}>Medical License Number</label>
                <input
                  type="text"
                  value={licenseNumber}
                  onChange={e => setLicenseNumber(e.target.value)}
                  placeholder="e.g. MCI-12345"
                  style={{
                    background: 'var(--slate-50)',
                    borderColor: 'var(--slate-200)',
                    color: 'var(--slate-900)',
                  }}
                />
                <p style={{ color: 'var(--slate-500)', fontSize: '0.76rem', marginTop: 6 }}>
                  Doctor accounts require admin approval before accessing patient data.
                </p>
              </div>
            )}

            <button
              type="submit"
              className={`btn btn-${theme.primary}`}
              style={{ width: '100%', marginTop: 8, padding: '12px' }}
              disabled={loading}
            >
              {loading ? (
                <span>{mode === 'register' ? 'Creating account...' : 'Signing in...'}</span>
              ) : (
                <>
                  <span>{mode === 'register' ? 'Create Doctor Account' : 'Sign In as Doctor'}</span>
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          </form>

          <div style={{ textAlign: 'center', marginTop: 16 }}>
            <button
              type="button"
              onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(''); setNotice('') }}
              style={{ background: 'transparent', border: 'none', color: 'var(--primary-600)', cursor: 'pointer', fontSize: '0.85rem', fontWeight: 600 }}
            >
              {mode === 'login' ? 'New here? Create an account' : 'Already have an account? Sign in'}
            </button>
          </div>

          <div style={{
            marginTop: 24,
            paddingTop: 20,
            borderTop: '1px solid var(--slate-200)',
            textAlign: 'center'
          }}>
            <p style={{ color: 'var(--slate-500)', fontSize: '0.8rem', marginBottom: 8 }}>
              <Link to="/patient/login" style={{ color: 'var(--teal-600)', fontWeight: 600 }}>Patient Portal</Link> &bull; 
              <a href="/admin/login" style={{ color: 'var(--slate-600)', fontWeight: 600 }}>Admin Login</a>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}