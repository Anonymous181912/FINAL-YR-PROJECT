import api from './api'

export async function requestAccess(patientId, scope = ['reports', 'prescriptions', 'history'], message = '') {
  const response = await api.post('/access/requests', { patient_id: patientId, scope, message })
  return response.data
}

export async function incomingRequests(status = null) {
  const params = status ? { status_filter: status } : {}
  const response = await api.get('/access/requests/incoming', { params })
  return response.data
}

export async function outgoingRequests() {
  const response = await api.get('/access/requests/outgoing')
  return response.data
}

export async function approveRequest(requestId, expiresInDays = 30, scope = null) {
  const response = await api.post(`/access/requests/${requestId}/approve`, {
    expires_in_days: expiresInDays,
    ...(scope ? { scope } : {}),
  })
  return response.data
}

export async function denyRequest(requestId) {
  const response = await api.post(`/access/requests/${requestId}/deny`)
  return response.data
}

export async function myGrants() {
  const response = await api.get('/access/grants/mine')
  return response.data
}

export async function doctorGrants() {
  const response = await api.get('/access/grants/doctor')
  return response.data
}

export async function revokeGrant(grantId) {
  await api.delete(`/access/grants/${grantId}`)
}

export async function myAuditTrail(limit = 100) {
  const response = await api.get('/audit/me', { params: { limit } })
  return response.data
}

export async function adminAuditSearch(filters = {}) {
  const response = await api.get('/audit/', { params: filters })
  return response.data
}
