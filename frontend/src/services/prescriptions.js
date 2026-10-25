import api from './api'

export async function createPrescription(payload) {
  // Trailing slash matches the backend route exactly; without it FastAPI
  // answers 307 to an absolute URL and browsers drop Authorization on the
  // cross-origin redirect (surfacing as a spurious 401/logout).
  const response = await api.post('/prescriptions/', payload)
  return response.data
}

export async function getPrescription(prescriptionId) {
  const response = await api.get(`/prescriptions/${prescriptionId}`)
  return response.data
}

export async function listDoctorPrescriptions(skip = 0, limit = 20) {
  const response = await api.get(`/prescriptions/doctor`, { params: { skip, limit } })
  return response.data
}

export async function listPatientPrescriptions(skip = 0, limit = 20) {
  const response = await api.get(`/prescriptions/patient`, { params: { skip, limit } })
  return response.data
}

export async function updatePrescription(prescriptionId, payload) {
  const response = await api.put(`/prescriptions/${prescriptionId}`, payload)
  return response.data
}

export async function deletePrescription(prescriptionId) {
  const response = await api.delete(`/prescriptions/${prescriptionId}`)
  return response.data
}

export async function generatePrescriptionPdf(prescriptionId) {
  const response = await api.post(`/prescriptions/${prescriptionId}/pdf`, {}, { responseType: 'blob' })
  return response.data
}

export function downloadPrescriptionPdf(blob, filename = 'prescription.pdf') {
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  window.URL.revokeObjectURL(url)
  document.body.removeChild(a)
}

export async function revokePrescription(prescriptionId) {
  const response = await api.post(`/prescriptions/${prescriptionId}/revoke`)
  return response.data
}

export async function issuePrescription(prescriptionId) {
  const response = await api.post(`/prescriptions/${prescriptionId}/issue`)
  return response.data
}

export async function scanPrescription(file) {
  const formData = new FormData()
  formData.append('file', file)
  const response = await api.post('/prescriptions/scan', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data
}

export async function verifyPrescriptionToken(token) {
  const response = await api.get(`/verify/prescription/${token}`)
  return response.data
}

export async function verifyEmergencyToken(token) {
  const response = await api.get(`/verify/emergency/${token}`)
  return response.data
}
