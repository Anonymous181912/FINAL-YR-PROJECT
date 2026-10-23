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
