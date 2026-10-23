import api from './api'

export async function getPatientHistory(order = 'desc', limit = 50) {
  const response = await api.get('/history/', { params: { order, limit } })
  return response.data
}

export async function getDoctorPatientHistory(patientId, order = 'desc', limit = 50) {
  const response = await api.get(`/history/patient/${patientId}`, { params: { order, limit } })
  return response.data
}
