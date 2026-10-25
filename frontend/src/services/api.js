import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
})

const PORTAL_LOGIN_BY_ROLE = {
  doctor: '/doctor/login',
  patient: '/patient/login',
  admin: '/admin/login',
}

function storedUser() {
  try {
    return JSON.parse(localStorage.getItem('user') || 'null')
  } catch {
    return null
  }
}

function portalLoginPath() {
  const role = storedUser()?.role
  return PORTAL_LOGIN_BY_ROLE[role] || '/patient/login'
}

function onLoginPage() {
  const path = window.location.pathname
  return (
    path.startsWith('/patient/login') ||
    path.startsWith('/doctor/login') ||
    path.startsWith('/admin/login') ||
    path === '/login'
  )
}

function clearSession() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('user')
}

// Shared in-flight refresh: parallel 401s trigger exactly one rotation.
let refreshPromise = null

function refreshAccessToken() {
  if (refreshPromise) return refreshPromise

  const refreshToken = localStorage.getItem('refresh_token')
  if (!refreshToken) return Promise.reject(new Error('No refresh token'))

  refreshPromise = axios
    .post('/api/v1/auth/refresh', { refresh_token: refreshToken })
    .then(({ data }) => {
      localStorage.setItem('access_token', data.access_token)
      if (data.refresh_token) localStorage.setItem('refresh_token', data.refresh_token)
      return data.access_token
    })
    .finally(() => {
      refreshPromise = null
    })

  return refreshPromise
}

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config
    const status = error.response?.status
    const url = config?.url || ''

    const notAuthFailure =
      status !== 401 ||
      !config ||
      config._retried ||
      url.includes('/auth/refresh') ||
      url.includes('/auth/login')

    if (notAuthFailure) return Promise.reject(error)

    // Never bounce requests that are already on a login screen (loop guard).
    if (onLoginPage()) return Promise.reject(error)

    config._retried = true
    const loginPath = portalLoginPath()

    try {
      const token = await refreshAccessToken()
      config.headers = { ...(config.headers || {}), Authorization: `Bearer ${token}` }
      return api(config)
    } catch {
      clearSession()
      if (!onLoginPage()) window.location.href = loginPath
      return Promise.reject(error)
    }
  }
)

export default api
