import api from './api'

export async function uploadReport(file, category, title) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('category', category)
  formData.append('title', title)

  const response = await api.post('/reports/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return response.data
}

export async function interpretReport(reportId, language = 'en') {
  const response = await api.post(`/reports/${reportId}/interpret`, null, { params: { language } })
  return response.data
}

export async function chatWithReport(reportId, question, history = []) {
  const response = await api.post(`/reports/${reportId}/chat`, { question, history })
  return response.data
}

export async function listReports(skip = 0, limit = 20, patientId = null) {
  const params = { skip, limit }
  if (patientId) params.patient_id = patientId
  const response = await api.get('/reports/', { params })
  return response.data
}

export async function getReport(reportId) {
  const response = await api.get(`/reports/${reportId}`)
  return response.data
}

export async function deleteReport(reportId) {
  await api.delete(`/reports/${reportId}`)
}

export async function getReportLabs(reportId) {
  const response = await api.get(`/reports/${reportId}/labs`)
  return response.data
}

export async function getLabTrends(test, patientId = null) {
  const params = { test }
  if (patientId) params.patient_id = patientId
  const response = await api.get('/reports/trends', { params })
  return response.data
}

export const LAB_TESTS = [
  'hemoglobin', 'rbc', 'wbc', 'platelets', 'hematocrit',
  'fasting_glucose', 'random_glucose', 'hba1c', 'total_cholesterol',
  'ldl', 'hdl', 'triglycerides', 'creatinine', 'urea_bun',
  'alt', 'ast', 'tsh', 'sodium', 'potassium', 'vitamin_d',
]
