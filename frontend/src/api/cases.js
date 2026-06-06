/* 案件相关 API */
import api from './index'

export function getCases(params = {}) {
  return api.get('/cases', { params })
}

export function getCase(id) {
  return api.get(`/cases/${id}`)
}

export function createCase(data) {
  return api.post('/cases', data)
}

export function updateCase(id, data) {
  return api.put(`/cases/${id}`, data)
}

export function deleteCase(id) {
  return api.delete(`/cases/${id}`)
}

export function advanceCase(id, note = '') {
  return api.post(`/cases/${id}/advance`, { note })
}

export function batchAdvance(caseIds) {
  return api.post('/cases/batch/advance', { case_ids: caseIds })
}

export function assignCase(id, lawyerId) {
  return api.post(`/cases/${id}/assign`, { lawyer_id: lawyerId })
}

export function batchAssign(caseIds, lawyerId) {
  return api.post('/cases/batch/assign', { case_ids: caseIds, lawyer_id: lawyerId })
}

export function addCaseLog(id, note) {
  return api.post(`/cases/${id}/log`, { note })
}

export function exportCasesCsv(params = {}) {
  return api.get('/cases/export/csv', { params, responseType: 'blob' })
}

export function generateCoreSummary(id) {
  return api.post(`/cases/${id}/generate-core-summary`)
}
