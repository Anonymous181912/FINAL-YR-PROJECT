import api from './api'

export async function listNotifications(unreadOnly = false) {
  const response = await api.get('/notifications/', { params: unreadOnly ? { unread_only: true } : {} })
  return response.data
}

export async function markNotificationRead(id) {
  const response = await api.patch(`/notifications/${id}/read`)
  return response.data
}

export async function markAllNotificationsRead() {
  const response = await api.post('/notifications/read-all')
  return response.data
}

export async function downloadEmergencyCard() {
  const response = await api.get('/patients/me/emergency-card', { responseType: 'blob' })
  return response.data
}

export async function rotateEmergencyToken() {
  const response = await api.post('/patients/me/emergency-token/rotate')
  return response.data
}

export async function revokeEmergencyToken() {
  await api.delete('/patients/me/emergency-token')
}
