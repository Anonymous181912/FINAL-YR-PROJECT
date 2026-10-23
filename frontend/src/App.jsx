import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate, Link } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth.jsx'
import Login from './pages/Login.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Reports from './pages/Reports.jsx'
import Prescriptions from './pages/Prescriptions.jsx'
import Patients from './pages/Patients.jsx'
import History from './pages/History.jsx'
import Profile from './pages/Profile.jsx'
import Admin from './pages/Admin.jsx'
import { VerifyPrescription, VerifyEmergency } from './pages/Verify.jsx'
import AccessPrivacy from './pages/AccessPrivacy.jsx'
import { ForgotPassword, ResetPassword } from './pages/PasswordReset.jsx'
import Layout from './Layout.jsx'
import api from './services/api'

function ProtectedRoute({ children, allowedRoles }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  if (allowedRoles && !allowedRoles.includes(user.role)) return <Navigate to="/dashboard" replace />
  return children
}

function LoadingSplash() {
  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      gap: 14,
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--slate-50)',
      color: 'var(--slate-600)',
    }}>
      <div className="loading-spinner" />
      <div style={{ fontWeight: 600 }}>Loading application...</div>
      <div style={{ fontSize: '0.85rem' }}>Checking your session</div>
    </div>
  )
}

function PendingApproval() {
  const { logout } = useAuth()
  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24, background: 'var(--slate-50)' }}>
      <div className="card" style={{ maxWidth: 480, textAlign: 'center' }}>
        <h2 style={{ marginBottom: 8 }}>Account pending approval</h2>
        <p style={{ color: 'var(--slate-500)', fontSize: '0.92rem', marginBottom: 12 }}>
          Your doctor account has been created and is waiting for admin verification.
          You will gain access to patient data once an administrator approves your account.
        </p>
        <p style={{ color: 'var(--slate-500)', fontSize: '0.85rem', marginBottom: 20 }}>
          You can still view your profile. Please check back later.
        </p>
        <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
          <Link to="/profile" className="btn btn-secondary">View Profile</Link>
          <button className="btn btn-ghost" onClick={() => { logout(); window.location.href = '/login' }}>Sign Out</button>
        </div>
      </div>
    </div>
  )
}

function NotFound() {
  return (
    <div style={{
      minHeight: '60vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 24,
    }}>
      <div className="card" style={{ maxWidth: 440, textAlign: 'center', marginBottom: 0 }}>
        <h2 style={{ marginBottom: 8 }}>Page not found.</h2>
        <p style={{ color: 'var(--slate-500)', fontSize: '0.92rem', marginBottom: 20 }}>
          The page you are looking for does not exist.
        </p>
        <Link to="/" className="btn btn-primary">Back to Home</Link>
      </div>
    </div>
  )
}

function AppRoutes() {
  const { user, authLoading } = useAuth()
  const [verifyState, setVerifyState] = useState({ loading: false, status: null })

  // Nothing redirects until auth initialization completes: unauthenticated
  // users always land on Login, never on a dashboard or blank page.
  useEffect(() => {
    let cancelled = false
    async function checkDoctor() {
      if (!user || user.role !== 'doctor') {
        if (!cancelled) setVerifyState({ loading: false, status: null })
        return
      }
      if (!cancelled) setVerifyState({ loading: true, status: null })
      try {
        const res = await api.get('/auth/me')
        if (!cancelled) setVerifyState({ loading: false, status: res.data?.verification_status || null })
      } catch {
        if (!cancelled) setVerifyState({ loading: false, status: null })
      }
    }
    if (!authLoading) checkDoctor()
    return () => { cancelled = true }
  }, [user, authLoading])

  if (authLoading || (user?.role === 'doctor' && verifyState.loading)) return <LoadingSplash />

  // Unverified doctors see the pending-approval screen for every route
  // except profile (so they can confirm their details) and login.
  const isPendingDoctor = user?.role === 'doctor' && verifyState.status && verifyState.status !== 'approved'

  return (
    <Routes>
      {/* Public verification pages: no login required (QR + emergency links). */}
      <Route path="/verify/:token" element={<VerifyPrescription />} />
      <Route path="/emergency/:token" element={<VerifyEmergency />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route
        path="/login"
        element={user ? <Navigate to="/dashboard" replace /> : <Login />}
      />
      {isPendingDoctor && (
        <>
          <Route path="/" element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }>
            <Route index element={<PendingApproval />} />
            <Route path="dashboard" element={<PendingApproval />} />
            <Route path="profile" element={
              <ProtectedRoute allowedRoles={['doctor', 'patient', 'admin']}>
                <Profile verificationStatus={verifyState.status} />
              </ProtectedRoute>
            } />
            <Route path="*" element={<PendingApproval />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </>
      )}
      {!isPendingDoctor && (
        <>
          <Route path="/" element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="reports" element={
              <ProtectedRoute allowedRoles={['doctor', 'patient']}>
                <Reports />
              </ProtectedRoute>
            } />
            <Route path="reports/:id" element={<Reports />} />
            <Route path="prescriptions" element={
              <ProtectedRoute allowedRoles={['doctor', 'patient']}>
                <Prescriptions />
              </ProtectedRoute>
            } />
            <Route path="patients" element={
              <ProtectedRoute allowedRoles={['doctor']}>
                <Patients />
              </ProtectedRoute>
            } />
            <Route path="history" element={
              <ProtectedRoute allowedRoles={['doctor', 'patient']}>
                <History />
              </ProtectedRoute>
            } />
            <Route path="profile" element={
              <ProtectedRoute allowedRoles={['doctor', 'patient', 'admin']}>
                <Profile />
              </ProtectedRoute>
            } />
            <Route path="access" element={
              <ProtectedRoute allowedRoles={['patient']}>
                <AccessPrivacy />
              </ProtectedRoute>
            } />
            <Route path="admin" element={
              <ProtectedRoute allowedRoles={['admin']}>
                <Admin />
              </ProtectedRoute>
            } />
            <Route path="*" element={<NotFound />} />
          </Route>
          {/* Unknown top-level route: controlled fallback, never a blank page. */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </>
      )}
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <Router>
        <AppRoutes />
      </Router>
    </AuthProvider>
  )
}
