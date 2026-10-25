import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate, Link } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth.jsx'
import Landing from './pages/Landing.jsx'
import PatientLogin from './pages/PatientLogin.jsx'
import DoctorLogin from './pages/DoctorLogin.jsx'
import AdminLogin from './pages/AdminLogin.jsx'
import PatientDashboard from './pages/PatientDashboard.jsx'
import DoctorDashboard from './pages/DoctorDashboard.jsx'
import PatientReports from './pages/PatientReports.jsx'
import DoctorReports from './pages/DoctorReports.jsx'
import PatientPrescriptions from './pages/PatientPrescriptions.jsx'
import DoctorPrescriptions from './pages/DoctorPrescriptions.jsx'
import PatientHistory from './pages/PatientHistory.jsx'
import DoctorPatients from './pages/DoctorPatients.jsx'
import PatientProfile from './pages/PatientProfile.jsx'
import DoctorProfile from './pages/DoctorProfile.jsx'
import DoctorAccess from './pages/DoctorAccess.jsx'
import DoctorHistory from './pages/DoctorHistory.jsx'
import PatientAccess from './pages/PatientAccess.jsx'
import Admin from './pages/Admin.jsx'
import { VerifyPrescription, VerifyEmergency } from './pages/Verify.jsx'
import { ForgotPassword, ResetPassword } from './pages/PasswordReset.jsx'
import PatientLayout from './layouts/PatientLayout.jsx'
import DoctorLayout from './layouts/DoctorLayout.jsx'
import AdminLayout from './layouts/AdminLayout.jsx'
import api from './services/api'

export function ProtectedRoute({ children, allowedRoles, portal }) {
  const { user } = useAuth()
  if (!user) {
    const loginPath = portal === 'doctor' ? '/doctor/login' : portal === 'admin' ? '/admin/login' : '/patient/login'
    return <Navigate to={loginPath} replace />
  }
  if (allowedRoles && !allowedRoles.includes(user.role)) {
    const dashboardPath = user.role === 'doctor' ? '/doctor/dashboard' : user.role === 'admin' ? '/admin/dashboard' : '/patient/dashboard'
    return <Navigate to={dashboardPath} replace />
  }
  if (portal && user.role !== portal && user.role !== 'admin') {
    const dashboardPath = user.role === 'doctor' ? '/doctor/dashboard' : '/patient/dashboard'
    return <Navigate to={dashboardPath} replace />
  }
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
          <Link to="/doctor/profile" className="btn btn-secondary">View Profile</Link>
          <button className="btn btn-ghost" onClick={() => { logout(); window.location.href = '/doctor/login' }}>Sign Out</button>
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

  const isPendingDoctor = user?.role === 'doctor' && verifyState.status && verifyState.status !== 'approved'

  return (
    <Routes>
      {/* Public verification pages: no login required (QR + emergency links). */}
      <Route path="/verify/:token" element={<VerifyPrescription />} />
      <Route path="/emergency/:token" element={<VerifyEmergency />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      
      {/* Landing Page */}
      <Route path="/" element={<Landing />} />
      
      {/* Patient Portal Routes */}
      <Route path="/patient/login" element={user?.role === 'patient' ? <Navigate to="/patient/dashboard" replace /> : <PatientLogin />} />
      <Route path="/patient/register" element={user?.role === 'patient' ? <Navigate to="/patient/dashboard" replace /> : <PatientLogin mode="register" />} />
      <Route path="/patient" element={
        <ProtectedRoute allowedRoles={['patient']} portal="patient">
          <PatientLayout />
        </ProtectedRoute>
      }>
        <Route path="dashboard" element={<PatientDashboard />} />
        <Route path="reports" element={<PatientReports />} />
        <Route path="reports/:id" element={<PatientReports />} />
        <Route path="prescriptions" element={<PatientPrescriptions />} />
        <Route path="history" element={<PatientHistory />} />
        <Route path="profile" element={<PatientProfile />} />
        <Route path="access" element={<PatientAccess />} />
        <Route path="*" element={<Navigate to="/patient/dashboard" replace />} />
      </Route>
      
      {/* Doctor Portal Routes */}
      <Route path="/doctor/login" element={user?.role === 'doctor' ? <Navigate to="/doctor/dashboard" replace /> : <DoctorLogin />} />
      <Route path="/doctor/register" element={user?.role === 'doctor' ? <Navigate to="/doctor/dashboard" replace /> : <DoctorLogin mode="register" />} />
      {isPendingDoctor && (
        <>
          <Route path="/doctor" element={
            <ProtectedRoute allowedRoles={['doctor']} portal="doctor">
              <DoctorLayout />
            </ProtectedRoute>
          }>
            <Route index element={<PendingApproval />} />
            <Route path="dashboard" element={<PendingApproval />} />
            <Route path="profile" element={
              <ProtectedRoute allowedRoles={['doctor']} portal="doctor">
                <DoctorProfile verificationStatus={verifyState.status} />
              </ProtectedRoute>
            } />
            <Route path="*" element={<PendingApproval />} />
          </Route>
          <Route path="/doctor/*" element={<Navigate to="/doctor" replace />} />
        </>
      )}
      {!isPendingDoctor && (
        <>
          <Route path="/doctor" element={
            <ProtectedRoute allowedRoles={['doctor']} portal="doctor">
              <DoctorLayout />
            </ProtectedRoute>
          }>
            <Route path="dashboard" element={<DoctorDashboard />} />
            <Route path="patients" element={<DoctorPatients />} />
            <Route path="prescriptions" element={<DoctorPrescriptions />} />
            <Route path="reports" element={<DoctorReports />} />
            <Route path="reports/:id" element={<DoctorReports />} />
            <Route path="history" element={<DoctorHistory />} />
            <Route path="access" element={<DoctorAccess />} />
            <Route path="profile" element={<DoctorProfile />} />
            <Route path="*" element={<Navigate to="/doctor/dashboard" replace />} />
          </Route>
          <Route path="/doctor/*" element={<Navigate to="/doctor" replace />} />
        </>
      )}
      
      {/* Admin Portal Routes */}
      <Route path="/admin/login" element={user?.role === 'admin' ? <Navigate to="/admin/dashboard" replace /> : <AdminLogin />} />
      <Route path="/admin" element={
        <ProtectedRoute allowedRoles={['admin']} portal="admin">
          <AdminLayout />
        </ProtectedRoute>
      }>
        <Route index element={<Navigate to="/admin/dashboard" replace />} />
        <Route path="dashboard" element={<Admin />} />
        <Route path="*" element={<Navigate to="/admin/dashboard" replace />} />
      </Route>
      
      {/* Legacy routes - redirect to appropriate portal */}
      <Route path="/login" element={<Navigate to="/patient/login" replace />} />
      <Route path="/register" element={<Navigate to="/patient/register" replace />} />
      <Route path="/dashboard" element={<Navigate to="/patient/dashboard" replace />} />
      
      {/* Fallback */}
      <Route path="*" element={<NotFound />} />
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