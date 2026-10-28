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

export async function getTrendSummary(patientId = null) {
  const params = {}
  if (patientId) params.patient_id = patientId
  const response = await api.get('/trends/summary', { params })
  return response.data
}

export async function getTrendDetail(canonicalTest, patientId = null) {
  const params = {}
  if (patientId) params.patient_id = patientId
  const response = await api.get(`/trends/${encodeURIComponent(canonicalTest)}`, { params })
  return response.data
}

export async function updateTrendPoint(canonicalTest, reportId, payload) {
  const response = await api.patch(
    `/trends/${encodeURIComponent(canonicalTest)}/points/${encodeURIComponent(reportId)}`,
    payload,
  )
  return response.data
}
