import api from './api'

export async function listPatients(search = '', skip = 0, limit = 20) {
  const response = await api.get('/patients/', { params: { search, skip, limit } })
  return response.data
}

export async function getPatient(patientId) {
  const response = await api.get(`/patients/${patientId}`)
  return response.data
}

export async function getMyPatientProfile() {
  const response = await api.get('/patients/me')
  return response.data
}

export async function searchPatients(query, limit = 20) {
  const response = await api.get('/patients/search', { params: { q: query, limit } })
  return response.data
}

export async function updateMyPatientProfile(payload) {
  const response = await api.put('/patients/me', payload)
  return response.data
}
