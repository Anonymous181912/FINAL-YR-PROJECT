import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './auth.jsx'
import { ProtectedRoute } from './App.jsx'

function renderGuard({ allowedRoles, portal, role, token }) {
  if (role) {
    localStorage.setItem('user', JSON.stringify({ user_id: 'u1', email: 'user@test.com', role, full_name: 'Test User' }))
  }
  if (token) localStorage.setItem('access_token', token)

  if (role) {
    vi.stubGlobal('fetch', vi.fn(async () => ({
      ok: true,
      json: async () => ({ id: 'u1', email: 'user@test.com', role, full_name: 'Test User' }),
    })))
  }

  return render(
    <MemoryRouter initialEntries={['/']}>
      <AuthProvider>
        <Routes>
          <Route
            path="/"
            element={
              <ProtectedRoute allowedRoles={allowedRoles} portal={portal}>
                <div>protected content</div>
              </ProtectedRoute>
            }
          />
          <Route path="/patient/login" element={<div>patient login</div>} />
          <Route path="/doctor/login" element={<div>doctor login</div>} />
          <Route path="/admin/login" element={<div>admin login</div>} />
          <Route path="/patient/dashboard" element={<div>patient dashboard</div>} />
          <Route path="/doctor/dashboard" element={<div>doctor dashboard</div>} />
          <Route path="/admin/dashboard" element={<div>admin dashboard</div>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>
  )
}

describe('ProtectedRoute guards', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.unstubAllGlobals()
  })

  it('sends unauthenticated visitors to the patient login portal', () => {
    renderGuard({ allowedRoles: ['patient'], portal: 'patient' })
    expect(screen.getByText('patient login')).toBeInTheDocument()
  })

  it('sends unauthenticated visitors to the doctor login portal', () => {
    renderGuard({ allowedRoles: ['doctor'], portal: 'doctor' })
    expect(screen.getByText('doctor login')).toBeInTheDocument()
  })

  it('sends unauthenticated visitors to the admin login portal', () => {
    renderGuard({ allowedRoles: ['admin'], portal: 'admin' })
    expect(screen.getByText('admin login')).toBeInTheDocument()
  })

  it('keeps a patient out of doctor routes', () => {
    renderGuard({ allowedRoles: ['doctor'], portal: 'doctor', role: 'patient', token: 't' })
    expect(screen.getByText('patient dashboard')).toBeInTheDocument()
  })

  it('keeps a doctor out of patient routes', () => {
    renderGuard({ allowedRoles: ['patient'], portal: 'patient', role: 'doctor', token: 't' })
    expect(screen.getByText('doctor dashboard')).toBeInTheDocument()
  })

  it('renders the protected page for the matching role', async () => {
    renderGuard({ allowedRoles: ['patient'], portal: 'patient', role: 'patient', token: 't' })
    expect(screen.getByText('protected content')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText('protected content')).toBeInTheDocument())
  })
})
