import { createContext, useContext, useState, useEffect } from 'react'

const AuthContext = createContext(null)

// The ONLY valid roles. The server is the source of truth for identity;
// anything else (stale toggle value, corrupt storage, unknown shape) must
// never drive role-based UI. Invalid state resolves to logged-out.
const VALID_ROLES = ['doctor', 'patient', 'admin']

function loadStoredUser() {
  try {
    const stored = localStorage.getItem('user')
    if (!stored) return null
    const parsed = JSON.parse(stored)
    if (!parsed || !VALID_ROLES.includes(parsed.role)) return null
    return parsed
  } catch {
    return null
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(loadStoredUser)
  // Three-state auth: loading (checking) -> authenticated | unauthenticated.
  // Nothing redirects until initialization completes.
  const [authLoading, setAuthLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function validateSession() {
      const stored = loadStoredUser()
      const token = localStorage.getItem('access_token')
      if (!stored || !token) {
        // No restorable session: drop fragments (e.g. token without user)
        // so a partial state can never look authenticated.
        localStorage.removeItem('user')
        localStorage.removeItem('access_token')
        if (!cancelled) {
          setUser(null)
          setAuthLoading(false)
        }
        return
      }
      try {
        const res = await fetch('/api/v1/auth/me', {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (!res.ok) throw new Error('invalid session')
        const me = await res.json()
        if (!me || !VALID_ROLES.includes(me.role)) throw new Error('invalid identity')
        if (!cancelled) {
          // Sync identity from the server (name/role truth lives backend-side).
          const synced = {
            user_id: me.id,
            email: me.email,
            role: me.role,
            full_name: me.full_name,
          }
          setUser(synced)
          localStorage.setItem('user', JSON.stringify(synced))
        }
      } catch {
        // Expired/deleted account/unreachable backend: clear and land on login.
        if (!cancelled) {
          localStorage.removeItem('user')
          localStorage.removeItem('access_token')
          setUser(null)
        }
      } finally {
        if (!cancelled) setAuthLoading(false)
      }
    }
    validateSession()
    return () => { cancelled = true }
  }, [])

  const login = (userData) => {
    const role = VALID_ROLES.includes(userData?.role) ? userData.role : null
    if (!role) return
    const clean = { ...userData, role }
    if (clean.refresh_token) {
      localStorage.setItem('refresh_token', clean.refresh_token)
      delete clean.refresh_token
    }
    setUser(clean)
    localStorage.setItem('user', JSON.stringify(clean))
    setAuthLoading(false)
  }

  const logout = async () => {
    // Phase 6c: invalidate the refresh token server-side (best effort).
    const refresh = localStorage.getItem('refresh_token')
    if (refresh) {
      try {
        await fetch('/api/v1/auth/logout', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refresh }),
        })
      } catch { /* offline logout still clears local state */ }
    }
    setUser(null)
    localStorage.removeItem('user')
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    setAuthLoading(false)
  }

  return (
    <AuthContext.Provider value={{ user, login, logout, authLoading }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
