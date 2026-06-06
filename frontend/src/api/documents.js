import api from './index'

export function uploadDocument(caseId, file) {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('case_id', caseId)
  return api.post('/documents/upload', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function getDocument(id) {
  return api.get(`/documents/${id}`)
}

export function reanalyzeDocument(id) {
  return api.post(`/documents/${id}/reanalyze`)
}

export function smartIngest(file) {
  const fd = new FormData()
  fd.append('file', file)
  return api.post('/documents/smart-ingest', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
}

export function confirmIngest(documentId, action, caseId = null, newCase = null) {
  return api.post('/documents/smart-ingest/confirm', {
    document_id: documentId,
    action,
    case_id: caseId,
    new_case: newCase,
  })
}

export function searchDocuments(query) {
  return api.get('/documents/search', { params: { q: query } })
}

export function smartIngestAsync(file) {
  const fd = new FormData()
  fd.append('file', file)
  return api.post('/documents/smart-ingest/async', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function getIngestTasks(status = null, config = {}) {
  const params = status ? { status } : {}
  return api.get('/documents/ingest-tasks', { params, ...config })
}

export function getSmartIngestResult(docId) {
  return api.get(`/documents/smart-ingest/result/${docId}`)
}

export function getIngestTaskCount(config = {}) {
  return api.get('/documents/ingest-tasks/count', config)
}

export function getIngestTaskText(taskId) {
  return api.get(`/documents/ingest-tasks/${taskId}/text`)
}
